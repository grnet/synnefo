# Copyright (C) 2010, 2011, 2012, 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A. OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from __future__ import with_statement
from fabric.api import hide, env, settings, local, roles
from fabric.operations import run, put, get
import fabric
import re
import os
import shutil
import tempfile
import ast
from snfdeploy.lib import debug, Conf, Env, disable_color
from snfdeploy import massedit
from snfdeploy.components import *
from snfdeploy.roles import ROLES, CONFLICTS


def abort(action):
    def inner(*args, **kwargs):
        try:
            return action(*args, **kwargs)
        except BaseException as e:
            abort = kwargs.get("abort", True)
            force = env.force
            if not abort or force:
                debug(env.host,
                      "WARNING: command failed. Continuing anyway...")
            else:
                fabric.utils.abort(e)
    return inner


@abort
def try_get(remote_path, local_path=None, **kwargs):
    if env.dry_run:
        debug(env.host, " * Fetching file localy... ", remote_path)
        return
    get(remote_path, local_path=local_path, **kwargs)


@abort
def try_put(local_path=None, remote_path=None, mode=0644, **kwargs):
    if env.dry_run:
        debug(env.host, " * Upload file... ", remote_path)
        return
    put(local_path=local_path, remote_path=remote_path, mode=mode)


@abort
def try_run(cmd, **kwargs):
    if env.dry_run:
        debug(env.host, cmd)
        return ""
    elif env.local:
        return local(cmd, capture=True, shell="/bin/bash")
    else:
        return run(cmd)


def install_package(package):
    debug(env.host, " * Installing package... ", package)
    apt_get = "export DEBIAN_FRONTEND=noninteractive ;" + \
              "apt-get install -y --force-yes "

    host_info = env.env.ips_info[env.host]
    env.env.update_packages(host_info.os)
    if ast.literal_eval(env.env.use_local_packages):
        with settings(warn_only=True):
            deb = local("ls %s/%s*%s_*.deb"
                        % (env.env.packages, package, host_info.os),
                        capture=True)
            if deb:
                debug(env.host,
                      " * Package %s found in %s..."
                      % (package, env.env.packages))
                try_put(deb, "/tmp/")
                try_run("dpkg -i /tmp/%s || "
                        % os.path.basename(deb) + apt_get + "-f")
                try_run("rm /tmp/%s" % os.path.basename(deb))
                return

    info = getattr(env.env, package)
    if info in \
            ["squeeze-backports", "squeeze", "stable",
             "testing", "unstable", "wheezy", "experimental"]:
        apt_get += " -t %s %s " % (info, package)
    elif info:
        apt_get += " %s=%s " % (package, info)
    else:
        apt_get += package

    try_run(apt_get)

    return


def customize_settings_from_tmpl(tmpl, replace):
    debug(env.host, " * Customizing template %s..." % tmpl)
    local = env.env.templates + tmpl
    _, custom = tempfile.mkstemp()
    shutil.copyfile(local, custom)
    for k, v in replace.iteritems():
        regex = "re.sub('%{0}%', '{1}', line)".format(k.upper(), v)
        massedit.edit_files([custom], [regex], dry_run=False)

    return custom


def get_node_info(ident):
    if ident in env.env.ips_info:
        return env.env.ips_info[ident]
    elif ident in env.env.hosts_info:
        return env.env.hosts_info[ident]
    elif ident in env.env.nodes_info:
        return env.env.nodes_info[ident]


def GetFromComponent(component, remote, local):
    c = GetSynnefoComponent(component)
    c.debug(" * Downloading: ", remote)
    with settings(host_string=c.node_info.ip):
        try_get(remote, local)


def PutToComponent(component, local, remote):
    c = GetSynnefoComponent(component)
    c.debug(" * Uploading: ", remote)
    with settings(host_string=c.node_info.ip):
        try_put(local, remote)


def RunComponentMethod(component, method, *args, **kwargs):
    c = GetSynnefoComponent(component)
    c.debug(" * Running method: ", method)
    with settings(host_string=c.node_info.ip):
        fn = getattr(c, method)
        ret = ""
        for cmd in fn(*args, **kwargs):
            ret += try_run(cmd)
        return ret


def GetSynnefoComponent(component):
    node_info = get_node_info(env.host)
    env.password = node_info.passwd
    return component(node_info, env)


def conflicting_exists(component):
    conflict = CONFLICTS.get(component, [])
    for c in conflict:
        cs = env.env.status.check_status(env.host, c)
        if cs:
            debug(env.host, "Conflicting component already exists", c.__name__)
            return True

    return False


def SetupSynnefoRole(role):
    debug("Setting up base configuration for: ", role)
    try:
        components = ROLES.get(role)
    except KeyError:
        debug(env.host, "Please give a valid role")
        return
    for c in components:
        if conflicting_exists(c):
            continue
        status = env.env.status.check_status(env.host, c)
        if status:
            debug(env.host, "Base configuration already exists", c.__name__)
        else:
            AddSynnefoComponent(c)
            if not env.dry_run:
                env.env.status.update_status(env.host, c, "ok")
                env.env.status.write_status()


class AddSynnefoComponent(object):

    def _run(self, commands):
        for c in commands:
            try_run(c)

    def _install(self, packages):
        for p in packages:
            install_package(p)

    def _configure(self, templates):
        for tmpl, replace, opts in templates:
            mode = opts.get("mode", 0644)
            remote = opts.get("remote", tmpl)
            custom = customize_settings_from_tmpl(tmpl, replace)
            try_put(custom, remote, mode)
            os.remove(custom)

    def __init__(self, component):
        self.c = GetSynnefoComponent(component)
        self.c.debug("Adding component..")

        self.c.debug(" * Checking prerequisites..")
        self._run(self.c.check())

        self.c.debug(" * Installing packages..")
        self._install(self.c.install())

        self.c.debug(" * Preparing configuration..")
        self._run(self.c.prepare())

        self.c.debug(" * Setting up configuration files..")
        self._configure(self.c.configure())

        self.c.debug(" * Restarting services..")
        self._run(self.c.restart())

        self.c.debug(" * Initializing setup..")
        self._run(self.c.initialize())

        self.c.debug(" * Testing setup..")
        self._run(self.c.test())
