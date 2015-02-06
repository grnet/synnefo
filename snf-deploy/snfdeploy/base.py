# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from fabric.api import env, local
from fabric.operations import run, put, get
from fabric.context_managers import quiet
import fabric
import os
import shutil
import tempfile
import glob
import time
import copy
from snfdeploy.lib import debug
from snfdeploy import massedit
from snfdeploy import config
from snfdeploy import status
from snfdeploy import context
from snfdeploy import constants


#
# Decorators to use on FabricRunner's methods (run, get, put)
#
def _try_and_abort(fn):
    """Do nothing is case of dry-run otherwise execute and abort"""
    def wrapper(*args, **kwargs):
        assert args
        cl = args[0]
        if config.dry_run:
            cl._debug(args[1])
            return
        try:
            return fn(*args, **kwargs)
        except BaseException as e:
            if not cl.abort or config.force:
                cl._debug("WARNING: command failed. Continuing anyway...")
            else:
                fabric.utils.abort(e)
    return wrapper


def _setup_fabric_env(fn):
    """Update fabric specific vars related to ssh"""
    def wrapper(*args, **kwargs):
        assert args
        cl = args[0]
        env.host = cl.node.name
        env.host_string = cl.node.ip
        env.password = cl.node.password
        env.user = cl.node.user
        env.always_use_pty = False
        env.pty = False
        env.shell = "/bin/bash -c"
        env.key_filename = config.ssh_key
        return fn(*args, **kwargs)
    return wrapper


def log(fn):
    def wrapper(*args, **kwargs):
        assert args
        cl = args[0]
        cl._debug(fn.__name__)
        return fn(*args, **kwargs)
    return wrapper


def run_cmds(fn):
    def wrapper(*args, **kwargs):
        """If used as decorator of a class method first argument is self."""
        cl = args[0]
        # do something before fn
        ret = str()
        for c in fn(*args, **kwargs):
            output = cl.run(c)
            if output:
                ret += output
        return ret
    return wrapper


def check_if_testing(fn):
    def wrapper(*args, **kwargs):
        assert args
        if config.testing_vm:
            return []
        else:
            return fn(*args, **kwargs)
    return wrapper


def _customize_settings_from_tmpl(tmpl, replace):
    local = config.template_dir + tmpl
    _, custom = tempfile.mkstemp()
    shutil.copyfile(local, custom)
    for k, v in replace.iteritems():
        regex = "re.sub('%{0}%', '{1}', line)".format(k.upper(), v)
        editor = massedit.Editor(dry_run=False)
        editor.set_code_expr([regex])
        editor.edit_file(custom)

    return custom


class FabricRunner(object):

    @_try_and_abort
    @_setup_fabric_env
    def put(self, local, remote, mode=0644):
        self._debug("Uploading %s .." % remote)
        if config.autoconf:
            shutil.copyfile(local, remote)
            os.chmod(remote, mode)
        else:
            put(local_path=local, remote_path=remote, mode=mode)

    @_try_and_abort
    @_setup_fabric_env
    def get(self, remote, local):
        self._debug("Downloading %s .." % remote)
        if config.autoconf:
            shutil.copyfile(remote, local)
        else:
            get(remote_path=remote, local_path=local)

    @_try_and_abort
    @_setup_fabric_env
    def run(self, cmd):
        self._debug("RunCmd %s .." % cmd)
        if config.autoconf:
            return local(cmd, capture=True, shell="/bin/bash")
        else:
            return run(cmd)


class ComponentRunner(FabricRunner):
    """Fabric wrapper for SynnefoComponent"""

    ORDER = [
        "check",
        "install",
        "prepare",
        "configure",
        "restart",
        "initialize",
        "test",
        ]

    def _check_conflicts(self):
        for c in self.conflicts:
            if status.check(c(self.ctx)):
                raise BaseException("Conflicting Component: %s " %
                                    c.__name__)

    def _check_status(self):
        if status.check(self):
            raise BaseException("Component already installed: %s " %
                                self.__class__.__name__)

    def _update_status(self):
        status.update(self)
        self._debug(constants.VALUE_OK)

    def _debug(self, msg):
        debug(str(self.ctx), "[%s]" % self.__class__.__name__, msg)

    def _install_package(self, package):
        self._debug(" * Installing package %s... " % package)
        apt_get = "export DEBIAN_FRONTEND=noninteractive ;" + \
                  "apt-get install -y --force-yes "

        if config.use_local_packages:
            with quiet():
                debs = glob.glob("%s/%s*.deb" % (config.package_dir, package))
                if debs:
                    deb = debs[0]
                    f = os.path.basename(deb)
                    self._debug(" * Package %s found in %s..."
                                % (package, config.package_dir))
                    self.put(deb, "/tmp/%s" % f)
                    cmd = """
dpkg -i /tmp/{0}
{2} -f
apt-mark hold {1}
""".format(f, package, apt_get)
                    self.run(cmd)
                    self.run("rm /tmp/%s" % f)
                    return

        info = config.get_package(package, self.node.os)
        if info in \
                ["squeeze-backports", "squeeze", "stable",
                 "testing", "unstable", "wheezy", "wheezy-backports"]:
            apt_get += " -t %s %s " % (info, package)
        elif info:
            apt_get += " %s=%s " % (package, info)
        else:
            apt_get += package

        self.run(apt_get)

        return

    def install(self):
        for p in self._install():
            self._install_package(p)

    def configure(self):
        for tmpl, replace, opts in self._configure():
            self._debug(" * Customizing template %s..." % tmpl)
            mode = opts.get("mode", 0644)
            remote = opts.get("remote", tmpl)
            custom = _customize_settings_from_tmpl(tmpl, replace)
            self.put(custom, remote, mode)
            os.remove(custom)

    def _setup(self):
        self.admin_pre()
        self.check()
        self.install()
        self.prepare()
        self.configure()
        self.restart()
        self.initialize()
        self.test()
        self.admin_post()

    def _check_and_install_required(self):
        ctx = self.ctx
        for c in self.required_components():
            c(ctx=ctx).setup()

    def setup(self):
        self._check_and_install_required()
        try:
            self._check_status()
            self._check_conflicts()
        except BaseException as e:
            self._debug(str(e))
            return

        self._setup()
        self._update_status()
        time.sleep(1)


class Component(ComponentRunner):

    REQUIRED_PACKAGES = []

    alias = None
    service = None

    def __init__(self, ctx=None, node=None):
        if not ctx:
            self.ctx = context.Context()
        else:
            self.ctx = copy.deepcopy(ctx)
        if node:
            self.ctx.node = node
        self.abort = True

    def required_components(self):
        return []

    @property
    def fqdn(self):
        return self.node

    @property
    def node(self):
        info = self.ctx.node_info
        info.alias = self.alias
        return info

    @property
    def cluster(self):
        return self.ctx.cluster_info

    @property
    def conflicts(self):
        return []

    def admin_pre(self):
        pass

    @run_cmds
    def check(self):
        """ Returns a list of bash commands that check prerequisites """
        return []

    def _install(self):
        """ Returns a list of debian packages to install """
        return self.REQUIRED_PACKAGES

    @run_cmds
    def prepare(self):
        """ Returs a list of bash commands that prepares the component """
        return []

    def _configure(self):
        """ Must return a list of tuples (tmpl_path, replace_dict, mode) """
        return []

    @run_cmds
    def initialize(self):
        """ Returs a list of bash commands that initialize the component """
        return []

    @run_cmds
    def test(self):
        """ Returs a list of bash commands that test existing installation """
        return []

    @run_cmds
    def restart(self):
        return []

    @run_cmds
    def clean(self):
        return []

    def admin_post(self):
        pass
