#!/bin/bash

if [ $# -ne 2 ]; then
  echo "$0 upstream_branch debian_branch"
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

cleanup()
{
    trap - EXIT

    if [ ${#CLEANUP[*]} -gt 0 ]; then
        LAST_ELEMENT=$((${#CLEANUP[*]}-1))
        REVERSE_INDEXES=$(seq ${LAST_ELEMENT} -1 0)
        for i in $REVERSE_INDEXES; do
            local cmd=${CLEANUP[$i]}
            $cmd
        done
    fi
}

add_cleanup() {
    local cmd=""
    for arg; do cmd+=$(printf "%q " "$arg"); done
    CLEANUP+=("$cmd")
}


add_checkpoint()
{
    commit=$(git reflog | head -n1 | cut -f 1 -d " ")
    add_cleanup git reset --hard $commit
    LASTCHECKPOINT=$commit
}

CLEANUP=( )

# The root of the git repository, no matter where we're called from
TOPLEVEL="$(git rev-parse --show-toplevel)"
CURRENT_BRANCH=$(parse_git_branch)

LOCALBRANCH="$CURRENT_BRANCH"
REMOTEUPSTREAM=$1
REMOTEDEBIAN=$2
PKGAREA=~/packages
BACKUPAREA=~/backup
BUILDAREA=$(mktemp -d --tmpdir=/tmp build-area.XXX)

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
trap cleanup EXIT

cd "$TOPLEVEL"

# Prerequisites: Test all important directories exist
test -d "$PKGAREA" || die "Package area directory $PKGAREA missing"
test -d "$BACKUPAREA" || die "Backup area directory $BACKUPAREA missing"

# Prerequisite: Test the dialog utility is available
dialog --help &>/dev/null || die "Could not run the 'dialog' utility"

# Test all needed branches exist and can be checked out
#TODO: check for up-to-date branches
git fetch origin $REMOTEUPSTREAM
git fetch origin $REMOTEDEBIAN

echo "##########################################################"
echo "Will build packages"
echo "under '$BUILDAREA',"
echo "from branch '$LOCALBRANCH'"
echo "with upstream branch '$REMOTEUPSTREAM',"
echo "and debian branch '$REMOTEDEBIAN'"
echo "##########################################################"
echo "Press Enter to continue..."
read

add_checkpoint

# Create a temporary debian branch to do everything
TMPDEBIAN=$(mktemp -u debian.XXX)
git branch --track $TMPDEBIAN  origin/$REMOTEDEBIAN
#add_cleanup git branch -D $TMPDEBIAN

git checkout $TMPDEBIAN
add_cleanup git checkout $LOCALBRANCH

add_checkpoint

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
  add_cleanup rm $TAGFILE
  dialog --inputbox "New Debian Tag: " 5 30 "debian/$version" 2>$TAGFILE
  git tag $(<$TAGFILE)
  add_cleanup git tag -d $(<$TAGFILE)
fi


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
cp -v "$BUILDAREA"/* "$PKGAREA"/ || true
cp -v "$BUILDAREA"/* "$BACKUPAREA"/ || true

# Revert the changes, altough everything should have taken
# place inside a temporary directory, and we can probably nuke everything
if ! $snap; then
  # here we can push the commits to the remote debian branch as they are
  echo "#################### All OK ###################"
  echo "git push --tags origin $TMPDEBIAN:$REMOTEDEBIAN"
  echo
fi

exit 0
