# Copyright 2011 GRNET S.A. All rights reserved.
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
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
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
#

import os
import sys

from contextlib import contextmanager
from fabric.api import *
from fabric.colors import *

env.project_root = "./"
env.develop = False
env.autoremove = True
env.packages = ['snf-pithos-lib', 'snf-pithos-backend', 'snf-pithos-app',
                'snf-pithos-tools']
env.deb_packages = ['snf-pithos-lib', 'snf-pithos-backend']
env.capture = False
env.colors = True
env.pypi_root = 'pypi'
env.roledefs = {
    'docs': ['docs.dev.grnet.gr'],
    'pypi': ['docs.dev.grnet.gr']
}

# coloured logging
notice = lambda x: sys.stdout.write(yellow(x) + "\n")
info = lambda x: sys.stdout.write(green(x) + "\n")
error = lambda x: sys.stdout.write(red(x) + "\n")


def dev():
    env.develop = True

# wrap local to respect global capturing setting from env.capture
oldlocal = local
def local(cmd, capture="default"):
    if capture != "default":
        capture = capture
    else:
        capture = env.capture
    return oldlocal(cmd, capture=capture)


def package_root(p):
    return os.path.join(env.project_root, p)


def remove_pkg(p):
    notice("uninstalling package: %s" % p)
    with lcd(package_root(p)):
        with settings(warn_only=True):
            local("pip uninstall %s -y" % p, env.capture)


def build_pkg(p):
    info ("building package: %s" % p)
    with lcd(package_root(p)):
        with settings(warn_only=True):
            local("rm -r dist build")
        local("python setup.py egg_info -d sdist")


def install_pkg(p):
    info("installing package: %s" % p)
    with lcd(package_root(p)):
        print local('pwd');
        if env.develop:
            local("python setup.py develop")
        else:
            local("python setup.py install")


def install(*packages):
    for p in packages:
        install_pkg("snf-%s" % p)


def buildall():
    for p in env.packages:
        build_pkg(p)
    collectdists()


def installall():
    for p in env.packages:
        install_pkg(p)

def collectdists():
    if os.path.exists("./packages"):
        notice("removing 'packages' directory")
        local("rm -r packages");

    local("mkdir packages");
    for p in env.packages:
        local("cp %s/dist/*.tar.gz ./packages/" % package_root(p));

def removeall():
    for p in env.packages:
        remove_pkg(p)


def remove(*packages):
    for p in packages:
        remove_pkg("snf-%s" % p)


#
# GIT helpers
#


def git(params, locl=True):
    cmd = local if locl else run
    return cmd("git %s" % params, capture=True)


def branch():
    return git("symbolic-ref HEAD").split("/")[-1]


@contextmanager
def co(c):
    current_branch = branch();
    git("checkout %s" % c)
    yield
    git("checkout %s" % current_branch)


#
# Debian packaging helpers
#


def builddeb(p, master="master", branch="debian-0.8"):
    with lcd(package_root(p)):
        with settings(warn_only=True):
            local("mkdir .git")
            local("python setup.py clean")
            local("git add synnefo/versions/*.py -f")
            local("git-buildpackage --git-upstream-branch=%s --git-debian-branch=%s \
--git-export=INDEX --git-ignore-new" % (master, branch))
            local("rm -rf .git")
            local("git reset synnefo/versions/*.py")


def builddeball(b="debian-0.8"):
    with co(b):
        for p in env.deb_packages:
            builddeb(p, b)
    collectdebs()


def collectdebs():
    build_area = env.get('build_area', '../build-area')
    for p in env.deb_packages:
        local("cp %s/%s*.deb ./packages/" % (build_area, p))

@roles('pypi')
def uploadtars():
    put("packages/*.tar.gz", 'www/pypi/')

