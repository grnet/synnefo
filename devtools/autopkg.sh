#!/bin/bash

if [ $# -ne 3 ]; then
  echo "$0 local_branch upstream_branch debian_branch"
  exit 1
fi

parse_git_branch()
{
    git branch 2> /dev/null | grep '^*' | sed 's/^*\ //g'
}

die()
{
    echo $* 1>&2
    exit 1
}

# The root of the git repository, no matter where we're called from
TOPLEVEL="$(git rev-parse --show-toplevel)"
CURRENT_BRANCH=$(parse_git_branch)

LOCALBRANCH="$CURRENT_BRANCH"
REMOTEUPSTREAM=$2
REMOTEDEBIAN=$3
PKGAREA=~/packages
BACKUPAREA=~/backup

PACKAGES="
  snf-astakos-app
  snf-common
  snf-webproject
  snf-cyclades-app
  snf-cyclades-gtools
  snf-tools
  snf-pithos-app
  snf-pithos-backend
  snf-pithos-tools"


set -e

# Prerequisites: Test all important directories exist
test -d "$PKGAREA" || die "Package area directory $PKGAREA missing"
test -d "$BACKUPAREA" || die "Backup area directory $BACKUPAREA missing"

# Prerequisite: Test the dialog utility is available
dialog --help &>/dev/null || die "Could not run the 'dialog' utility"

# Test all needed branches exist and can be checked out
#TODO: check for up-to-date branches
git checkout $REMOTEUPSTREAM || die "Could not checkout $REMOTEUPSTREAM"
git checkout $REMOTEDEBIAN || die "Could not checkout $REMOTEDEBIAN"
git checkout $LOCALBRANCH || die "Could not checkout $LOCALBRANCH"

# Move everything into a temp directory under /tmp
# ACHTUNG: "origin" is now the original toplevel directory of the git repo
TEMPAREA=$(mktemp -d)
cd "$TEMPAREA"
git clone "$TOPLEVEL" synnefo
cd synnefo
BUILDAREA="$TEMPAREA"/build-area

echo "Will build packages under $TEMPAREA, from branch $LOCALBRANCH"
echo "with upstream branch $REMOTEUPSTREAM, and debian branch $REMOTEDEBIAN"
echo "Press Enter to continue..."
read

# Create a temporary debian branch to do everything
TMPDEBIAN=$(mktemp -u debian.XXX)
git checkout --track origin/$REMOTEDEBIAN -b $TMPDEBIAN

# Whether we are in snapshot or release mode
snap=false
mrgextra=-m
dchextra=-R
mrgmsg="Merge branch '$REMOTEUPSTREAM' into $REMOTEDEBIAN"
dialog --defaultno --yesno "Create Snapshot?" 5 20 && snap=true && dchextra=-S && mrgextra= && mrgmsg=

# merge local branch into tmp branch with a nice commit message,
# so it can be pushed as is to upstream debian
git merge --no-edit $mrgextra ${mrgextra:+"$mrgmsg"} $LOCALBRANCH

# auto edit Debian changelog depending on Snapshot or Release mode
export EDITOR=/usr/bin/vim
git-dch --debian-branch=$TMPDEBIAN --git-author --ignore-regex=".*" --multimaint-merge --since=HEAD $dchextra
git add debian/changelog

# get version from the changelog
# we add a git tag here, so setup.py sdist works as expected
# FIXME: This is a workaround for the way Synnefo packages determine
#        the versions for their Python packages
version=$(IFS="()" ; read  x v x < debian/changelog  ; echo $v)
if ! $snap; then
  git commit -s -a -m "Bump new upstream version"
  TAGFILE=$(mktemp -t tag.XXX)
  dialog --inputbox "New Debian Tag: " 5 30 "debian/$version" 2>$TAGFILE
  git tag $(<$TAGFILE)
fi

mkdir "$BUILDAREA"

for p in $PACKAGES; do

  cd  $p
  python setup.py sdist
  grep "__version_vcs" -r . -l -I | xargs git add -f
  cd -

done

# Build all packages
git-buildpackage --git-export-dir="$BUILDAREA" \
                 --git-upstream-branch=$REMOTEUPSTREAM \
                 --git-debian-branch=$TMPDEBIAN \
                 --git-export=INDEX \
                 --git-ignore-new -sa

# do some dirty backup
# pkgarea might be needed by auto-deploy tool
rm -f "$PKGAREA"/* || true
cp -v "$BUILDAREA"/*deb "$PKGAREA"/ || true
cp -v "$BUILDAREA"/* "$BACKUPAREA"/ || true

# Revert the changes, altough everything should have taken
# place inside a temporary directory, and we can probably nuke everything
git reset --hard HEAD
if $snap; then
  git checkout $LOCALBRANCH
  git branch -D $TMPDEBIAN
else
  # here we can push the commits to the remote debian branch as they are
  echo "########### All OK #####################"
  echo "IF you want to push the temp debian branch to upstream $REMOTEDEBIAN,"
  echo "you may run this inside $TEMPAREA:"
  echo "git push --tags origin $TMPDEBIAN:$REMOTEDEBIAN"
  echo "git checkout $LOCALBRANCH"
  echo
  echo "Please also remember to remove $TEMPAREA."
  echo
  echo "############ Revert ######################"
  echo "git tag -d " $(<$TAGFILE)
  rm $TAGFILE
fi
