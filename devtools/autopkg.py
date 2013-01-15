# Copyright 2012 GRNET S.A. All rights reserved.
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

import git
import os
import sys
from sh import mktemp, cd, rm, git_dch, python
from optparse import OptionParser

try:
    from colors import red, green
except ImportError:
    red = lambda x: x
    green = lambda x: x

print_red = lambda x: sys.stdout.write(red(x) + "\n")
print_green = lambda x: sys.stdout.write(green(x) + "\n")

AVAILABLE_MODES = ["release", "snapshot"]
PACKAGES = (
  "snf-astakos-app",
  "snf-common",
  "snf-webproject",
  "snf-cyclades-app",
  "snf-cyclades-gtools",
  "snf-tools",
  "snf-pithos-app",
  "snf-pithos-backend",
  "snf-pithos-tools",
)


def main():
    parser = OptionParser(usage="usage: %prog [options] mode",
                          version="%prog 1.0")
    parser.add_option("-k", "--keep-repo",
                      action="store_true",
                      dest="keep_repo",
                      default=False,
                      help="Do not delete the cloned repository")
    parser.add_option("-b", "--build-dir",
                      dest="build_dir",
                      default=None,
                      help="Directory to store created pacakges")
    parser.add_option("-r", "--repo-dir",
                     dest="repo_dir",
                     default=None,
                     help="Directory to clone repository")
    parser.add_option("-d", "--dirty",
                     dest="force_dirty",
                     default=False,
                     action="store_true",
                     help="Do not check if working directory is dirty")

    (options, args) = parser.parse_args()

    mode = args[0]
    if mode not in AVAILABLE_MODES:
        raise ValueError(red("Invalid argument! Mode must be one: %s"
                         % ", ".join(AVAILABLE_MODES)))

    # Do not prompt for merge message. Required for some Git versions
    os.environ["GITFLOW_BUILD_MODE"] = mode

    try:
        original_repo = git.Repo(".")
    except git.git.InvalidGitRepositoryError:
        raise RuntimeError(red("Current directory is not git repository."))

    if original_repo.is_dirty() and not options.force_dirty:
        toplevel = original_repo.working_dir
        raise RuntimeError(red("Repository %s is dirty." % toplevel))

    repo_dir = options.repo_dir
    if not repo_dir:
        repo_dir = mktemp("-d", "/tmp/synnefo-build-repo-XXX").stdout.strip()
        print_green("Created temporary directory '%s' for the cloned repo."
                    % repo_dir)

    repo = original_repo.clone(repo_dir)
    print_green("Cloned current repository to '%s'." % repo_dir)

    reflog_hexsha = repo.head.log()[-1].newhexsha
    print "Latest Reflog entry is %s" % reflog_hexsha

    branch = repo.head.reference.name
    if branch == "master":
        debian_branch = "debian"
    else:
        debian_branch = "debian-" + branch

    try:
        repo.references[debian_branch]
    except IndexError:
        # Branch does not exist
        # FIXME: remove hard-coded strings..
        if branch == "debian":
            repo.git.branch("--track", debian_branch, "origin/debian")
        else:
            repo.git.branch("--track", debian_branch, "origin/debian-develop")

    repo.git.checkout(debian_branch)
    print_green("Changed to branch '%s'" % debian_branch)

    repo.git.merge(branch)
    print_green("Merged branch '%s' into '%s'" % (branch, debian_branch))

    cd(repo_dir)
    version = python(repo_dir + "/devtools/version.py", "debian").strip()
    print_green("The new debian version will be: '%s'" % version)

    dch = git_dch("--debian-branch=%s" % debian_branch,
            "--git-author",
            "--ignore-regex=\".*\"",
            "--multimaint-merge",
            "--since=HEAD",
            "--new-version=%s" % version)
    print_green("Successfully ran '%s'" % " ".join(dch.cmd))

    os.system("vim debian/changelog")
    repo.git.add("debian/changelog")

    if mode == "release":
        repo.git.commit("-s", "-a", "-m", "Bump new upstream version")
        if branch == "master":
            repo.git.tag("debian/" + version)

    for package in PACKAGES:
        # python setup.py should run in its directory
        cd(package)
        package_dir = repo_dir + "/" + package
        res = python(package_dir + "/setup.py", "sdist", _out=sys.stdout)
        cd("../")
        print res.stdout

    # Add version.py files to repo
    os.system("grep \"__version_vcs\" -r . -l -I | xargs git add -f")

    build_dir = options.build_dir
    if not options.build_dir:
        build_dir = mktemp("-d", "/tmp/synnefo-build-XXX").stdout.strip()
        print_green("Created directory '%s' to store the .deb files." %
                     build_dir)

    os.system("git-buildpackage --git-export-dir=%s --git-upstream-branch=%s"
              " --git-debian-branch=%s --git-export=INDEX --git-ignore-new -sa"
              % (build_dir, branch, debian_branch))

    if not options.keep_repo:
        print_green("Removing cloned repo '%s'." % repo_dir)
        rm("-r", repo_dir)
    else:
        print_green("Repository dir '%s'" % repo_dir)

    print_green("Completed. Version '%s', build area: '%s'"
                % (version, build_dir))


if __name__ == "__main__":
    main()
