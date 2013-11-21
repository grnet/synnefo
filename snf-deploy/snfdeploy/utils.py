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


def abort(action):
    def inner(*args, **kwargs):
        try:
            return action(*args, **kwargs)
        except BaseException as e:
            abort = kwargs.get("abort", True)
            if not abort:
                 debug(env.host, "WARNING: command failed. Continuing anyway...")
            else:
                 fabric.utils.abort(e)
    return inner


@abort
def try_get(remote_path, local_path=None, **kwargs):
    get(remote_path, local_path=local_path, **kwargs)


@abort
def try_put(local_path=None, remote_path=None, **kwargs):
    put(local_path=local_path, remote_path=remote_path, **kwargs)



@abort
def try_run(cmd, **kwargs):
    if env.local:
        return local(cmd, capture=True)
    else:
        return run(cmd)


def install_package(package):
    debug(env.host, " * Installing package %s..." % package)
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
             "testing", "unstable", "wheezy"]:
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


