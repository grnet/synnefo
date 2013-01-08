#!/usr/bin/env python
#
# Copyright (C) 2010, 2011, 2012 GRNET S.A. All rights reserved.
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


import os
import re
import sys
import pprint
import subprocess
from distutils import log
from collections import namedtuple


# Branch types:
# builds_snapshot: Whether the branch can produce snapshot builds
# builds_release: Whether the branch can produce release builds
# versioned: Whether the name of the branch defines a specific version
# allowed_version_re: A regular expression describing allowed values for
#                     base_version in this branch
branch_type = namedtuple("branch_type", ["builds_snapshot", "builds_release",
                                         "versioned", "allowed_version_re"])
VERSION_RE = "[0-9]+\.[0-9]+"
BRANCH_TYPES = {
    "feature": branch_type(True, False, False, "^%snext$" % VERSION_RE),
    "develop": branch_type(True, False, False, "^%snext$" % VERSION_RE),
    "release": branch_type(True, True, True,
                           "^(?P<bverstr>%s)rc[1-9][0-9]*$" % VERSION_RE),
    "master": branch_type(False, True, False,
                          "^%s$" % VERSION_RE),
    "hotfix": branch_type(True, True, True,
                          "^(?P<bverstr>^%s\.[1-9][0-9]*)$" % VERSION_RE)}
BASE_VERSION_FILE = "version"


def callgit(cmd):
    p = subprocess.Popen(["/bin/sh", "-c", cmd],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    output = p.communicate()[0].strip()
    if p.returncode != 0:
        log.error("Command '%s' failed with output:\n%s" % (cmd, output))
        raise subprocess.CalledProcessError(p.returncode, cmd, output)
    return output


def vcs_info():
    """
    Return current git HEAD commit information.

    Returns a tuple containing
        - branch name
        - commit id
        - commit count
        - git describe output
        - path of git toplevel directory

    """
    try:
        branch = callgit("git rev-parse --abbrev-ref HEAD")
        revid = callgit("git rev-parse --short HEAD")
        revno = int(callgit("git rev-list HEAD|wc -l"))
        desc = callgit("git describe --tags")
        toplevel = callgit("git rev-parse --show-toplevel")
    except subprocess.CalledProcessError:
        log.error("Could not retrieve git information. " +
                  "Current directory not a git repository?")
        raise

    info = namedtuple("vcs_info", ["branch", "revid", "revno",
                                   "desc", "toplevel"])

    return info(branch=branch, revid=revid, revno=revno, desc=desc,
                toplevel=toplevel)


def base_version(vcs_info):
    """Determine the base version from a file in the repository"""

    f = open(os.path.join(vcs_info.toplevel, BASE_VERSION_FILE))
    lines = [l.strip() for l in f.readlines()]
    l = [l for l in lines if not l.startswith("#")]
    if len(l) != 1:
        raise ValueError("File '%s' should contain a single non-comment line.")
    return l[0]


def build_mode():
    """Determine the build mode from the value of $GITFLOW_BUILD_MODE"""
    try:
        mode = os.environ["GITFLOW_BUILD_MODE"]
        assert mode == "release" or mode == "snapshot"
    except (KeyError, AssertionError):
        raise ValueError("GITFLOW_BUILD_MODE environment variable must be "
                         "'release' or 'snapshot'")
    return mode


def python_version(base_version, vcs_info, mode):
    """Generate a Python distribution version following devtools conventions.

    This helper generates a Python distribution version from a repository
    commit, following devtools conventions. The input data are:
        * base_version: a base version number, presumably stored in text file
          inside the repository, e.g., /version
        * vcs_info: vcs information: current branch name and revision no
        * mode: "snapshot", or "release"

    This helper assumes a git branching model following:
    http://nvie.com/posts/a-successful-git-branching-model/

    with 'master', 'develop', 'release-X', 'hotfix-X' and 'feature-X' branches.

    General rules:
    a) any repository commit can get as a Python version
    b) a version is generated either in 'release' or in 'snapshot' mode
    c) the choice of mode depends on the branch, see following table.

    A python version is of the form A_NNN,
    where A: X.Y.Z{,next,rcW} and NNN: a revision number for the commit,
    as returned by vcs_info().

    For every combination of branch and mode, releases are numbered as follows:

    BRANCH:  /  MODE: snapshot        release
    --------          ------------------------------
    feature           0.14next_150    N/A
    develop           0.14next_151    N/A
    release           0.14rc2_249     0.14rc2
    master            N/A             0.14
    hotfix            0.14.1rc6_121   0.14.1rc6
                      N/A             0.14.1

    The suffix 'next' in a version name is used to denote the upcoming version,
    the one being under development in the develop and release branches.
    Version '0.14next' is the version following 0.14, and only lives on the
    develop and feature branches.

    The suffix 'rc' is used to denote release candidates. 'rc' versions live
    only release and hotfix branches.

    Suffixes 'next' and 'rc' have been chosen to ensure proper ordering
    according to setuptools rules:

        http://www.python.org/dev/peps/pep-0386/#setuptools

    Every branch uses a value for A so that all releases are ordered based
    on the branch they came from, so:

    So
        0.13next < 0.14rcW < 0.14 < 0.14next < 0.14.1

    and

    >>> V("0.14next") > V("0.14")
    True
    >>> V("0.14next") > V("0.14rc7")
    True
    >>> V("0.14next") > V("0.14.1")
    False
    >>> V("0.14rc6") > V("0.14")
    False
    >>> V("0.14.2rc6") > V("0.14.1")
    True

    The value for _NNN is chosen based of the revision number of the specific
    commit. It is used to ensure ascending ordering of consecutive releases
    from the same branch. Every version of the form A_NNN comes *before*
    than A: All snapshots are ordered so they come before the corresponding
    release.

    So
        0.14next_* < 0.14
        0.14.1_* < 0.14.1
        etc

    and

    >>> V("0.14next_150") < V("0.14next")
    True
    >>> V("0.14.1next_150") < V("0.14.1next")
    True
    >>> V("0.14.1_149") < V("0.14.1")
    True
    >>> V("0.14.1_149") < V("0.14.1_150")
    True

    Combining both of the above, we get
       0.13next_* < 0.13next < 0.14rcW_* < 0.14rcW < 0.14_* < 0.14
       < 0.14next_* < 0.14next < 0.14.1_* < 0.14.1

    and

    >>> V("0.13next_102") < V("0.13next")
    True
    >>> V("0.13next") < V("0.14rc5_120")
    True
    >>> V("0.14rc3_120") < V("0.14rc3")
    True
    >>> V("0.14rc3") < V("0.14_1")
    True
    >>> V("0.14_120") < V("0.14")
    True
    >>> V("0.14") < V("0.14next_20")
    True
    >>> V("0.14next_20") < V("0.14next")
    True

    Note: one of the tests above fails because of constraints in the way
    setuptools parses version numbers. It does not affect us because the
    specific version format that triggers the problem is not contained in the
    table showing allowed branch / mode combinations, above.


    """

    branch = vcs_info.branch

    # If it's a debian branch, ignore starting "debian-"
    brnorm = branch
    if brnorm == "debian":
        brnorm = "debian-master"
    if brnorm.startswith("debian-"):
        brnorm = brnorm.split("debian-")[1]

    # Sanity checks
    if "-" in brnorm:
        btypestr = brnorm.split("-")[0]
        bverstr = brnorm.split("-")[1]
        if bverstr == "":
            raise ValueError("Malformed branch name '%s'" % branch)
        versioned = True
    else:
        btypestr = branch
        versioned = False
    try:
        btype = BRANCH_TYPES[btypestr]
    except KeyError:
        allowed_branches = ", ".join(x for x in BRANCH_TYPES.keys())
        raise ValueError("Malformed branch name '%s', cannot classify as one "
                         "of %s" % (btypestr, allowed_branches))

    if versioned != btype.versioned:
        raise ValueError(("Branch name '%s' should %s contain version" %
                          (branch, "not" if versioned else "")))
    if btype.versioned and not re.match(VERSION_RE, bverstr):
        raise ValueError(("Malformed version '%s' in branch name '%s'" %
                          (bverstr, branch)))

    m = re.match(btype.allowed_version_re, base_version)
    if not m or (btype.versioned and m.groupdict()["bverstr"] != bverstr):
        raise ValueError(("Base version '%s' unsuitable for branch name '%s'" %
                         (base_version, branch)))

    if mode not in ["snapshot", "release"]:
        raise ValueError(("Specified mode '%s' should be one of 'snapshot' or "
                          "'release'" % mode))
    snap = (mode == "snapshot")

    if ((snap and not btype.builds_snapshot) or
        (not snap and not btype.builds_release)):
        raise ValueError(("Invalid mode '%s' in branch type '%s'" %
                          (mode, btypestr)))

    if snap:
        v = "%s_%d_%s" % (base_version, vcs_info.revno, vcs_info.revid)
    else:
        v = base_version
    return v


def debian_version_from_python_version(pyver):
    """Generate a debian package version from a Python version.

    This helper generates a Debian package version from a Python version,
    following devtools conventions.

    Debian sorts version strings differently compared to setuptools:
    http://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Version

    Initial tests:

    >>> debian_version("3") < debian_version("6")
    True
    >>> debian_version("3") < debian_version("2")
    False
    >>> debian_version("1") == debian_version("1")
    True
    >>> debian_version("1") != debian_version("1")
    False
    >>> debian_version("1") >= debian_version("1")
    True
    >>> debian_version("1") <= debian_version("1")
    True

    This helper defines a 1-1 mapping between Python and Debian versions,
    with the same ordering.

    Debian versions are ordered in the same way as Python versions:

    >>> D("0.14next") > D("0.14")
    True
    >>> D("0.14next") > D("0.14rc7")
    True
    >>> D("0.14next") > D("0.14.1")
    False
    >>> D("0.14rc6") > D("0.14")
    False
    >>> D("0.14.2rc6") > D("0.14.1")
    True

    and

    >>> D("0.14next_150") < D("0.14next")
    True
    >>> D("0.14.1next_150") < D("0.14.1next")
    True
    >>> D("0.14.1_149") < D("0.14.1")
    True
    >>> D("0.14.1_149") < D("0.14.1_150")
    True

    and

    >>> D("0.13next_102") < D("0.13next")
    True
    >>> D("0.13next") < D("0.14rc5_120")
    True
    >>> D("0.14rc3_120") < D("0.14rc3")
    True
    >>> D("0.14rc3") < D("0.14_1")
    True
    >>> D("0.14_120") < D("0.14")
    True
    >>> D("0.14") < D("0.14next_20")
    True
    >>> D("0.14next_20") < D("0.14next")
    True

    """
    return pyver.replace("_", "~").replace("rc", "~rc")


def debian_version(base_version, vcs_info, mode):
    p = python_version(base_version, vcs_info, mode)
    return debian_version_from_python_version(p)


def update_version(module, name="version", root="."):
    """
    Generate or replace version.py as a submodule of `module`.

    This is a helper to generate/replace a version.py file containing version
    information as a submodule of passed `module`.

    """

    # FIXME: exit or fail if not in development environment?
    v = vcs_info()
    b = base_version(v)
    mode = build_mode()
    paths = [root] + module.split(".") + ["%s.py" % name]
    module_filename = os.path.join(*paths)
    content = """
__version__ = "%(version)s"
__version_info__ = __version__.split(".")
__version_vcs_info__ = %(vcs_info)s
    """ % dict(version=python_version(b, v, mode),
            vcs_info=pprint.PrettyPrinter().pformat(dict(v._asdict())))

    module_file = file(module_filename, "w+")
    module_file.write(content)
    module_file.close()


if __name__ == "__main__":
    v = vcs_info()
    b = base_version(v)
    mode = build_mode()

    try:
        arg = sys.argv[1]
        assert arg == "python" or arg == "debian"
    except IndexError:
        raise ValueError("A single argument, 'python' or 'debian is required")

    if arg == "python":
        print python_version(b, v, mode)
    elif arg == "debian":
        print debian_version(b, v, mode)
