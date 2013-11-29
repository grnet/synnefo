# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

import pkg_resources
import os
import pprint


def get_dist_from_module(modname):
    pkgroot = pkg_resources.get_provider(modname).egg_root
    return list(pkg_resources.find_distributions(pkgroot))[0]


def get_dist(dist_name):
    return pkg_resources.get_distribution(dist_name)


def get_dist_version(dist_name):
    """
    Get the version for the specified distribution name
    """
    try:
        return get_dist(dist_name).version
    except Exception:
        return 'unknown'


def get_component_version(modname):
    """
    Return the version of a synnefo module/package based on its
    corresponding distributed package version
    """
    try:
        try:
            return __import__('synnefo.versions.%s' % modname,
                              fromlist=['synnefo.versions']).__version__
        except ImportError:
            return "unknown"
    except Exception:
        return 'unknown'


def vcs_info():
    """
    Return current git HEAD commit information.

    Returns a tuple containing
        - branch name
        - commit id
        - commit index
        - git describe output
    """
    import subprocess
    callgit = lambda(cmd): subprocess.Popen(
        ['/bin/sh', '-c', cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE).communicate()[0].strip()

    branch = callgit('git branch | grep -Ei "\* (.*)" | cut -f2 -d" "')
    revid =\
        callgit("git --no-pager log --max-count=1 | cut -f2 -d' ' | head -1")
    revno = callgit('git --no-pager log --oneline | wc -l')
    desc = callgit('git describe --tags')

    return branch, revid, revno, desc


def get_version_from_describe(describe):
    """
    Package version based on `git describe` output. Compatible with setuptools
    version format

    >>> get_version_from_describe("v0.8.0")
    '0.8.0'
    >>> get_version_from_describe("debian/v0.8.0")
    '0.8.0'
    >>> get_version_from_describe("0.8.0")
    '0.8.0'
    >>> get_version_from_describe("v0.8.0-34-g8f9a1bf")
    '0.8.0-34-g8f9a1bf'
    >>> get_version_from_describe("debian/v0.8.0-34-g8f9a1bf")
    '0.8.0-34-g8f9a1bf'
    """

    version = describe.split("/")[-1].lstrip('v')
    version = version.lstrip('v')
    return version


def update_version_old(module, name='version', root="."):
    """
    Helper util to generate/replace a version.py file containing version
    information retrieved from get_version_from_describe as a submodule of
    passed `module`
    """

    # exit early if not in development environment
    if not os.path.exists(os.path.join(root, '..', '.git')) and\
       not os.path.exists(os.path.join(root, '.git')):
            return

    paths = [root] + module.split(".") + ["%s.py" % name]
    module_filename = os.path.join(*paths)
    content = """
__version__ = "%(version)s"
__version_info__ = __version__.split(".")
__version_vcs_info__ = %(vcs_info)s
    """ % dict(version=get_version_from_describe(vcs_info()[3]),
               vcs_info=pprint.PrettyPrinter().pformat(vcs_info()))

    module_file = file(module_filename, "w+")
    module_file.write(content)
    module_file.close()


def update_version(module, name='version', root='.'):
    try:
        from devflow import versioning
        return versioning.update_version(module, name, root)
    except ImportError:
        import sys
        paths = [root] + module.split(".") + ["%s.py" % name]
        module_filename = os.path.join(*paths)
        sys.stdout.write("WARNING: Cannot update version because `devflow` is"
                         " not installed. Please make sure to manually"
                         " update version file: '%s'\n" % module_filename)
