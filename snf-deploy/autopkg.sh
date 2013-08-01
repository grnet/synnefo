#!/bin/bash

usage(){

  echo "
Usage: $0: [options]
  -h, --help          Prints this help message
  --debian [branch]   Local debian branch to use (default debian)
  --upstream [branch] Local upstream branch to use (default master)
  --remote [repo]     Remote repo to use (default origin)
  --packages [dir]    Where to store the created packages (default ~/packages)
  --validate          Fetch remote repo branches and
                      check if local are up-to-date (default false)
  --push              Whether to push upstream (default false)
"
  exit 1
}

parse_git_branch()
{
    git branch 2> /dev/null | grep '^*' | sed 's/^*\ //g'
}

die()
{
    echo -e $* 1>&2
    echo Aborting.
    exit 1
}

cleanup()
{
    trap - EXIT

    echo -n Cleaning up...
    if [ ${#CLEANUP[*]} -gt 0 ]; then
        LAST_ELEMENT=$((${#CLEANUP[*]}-1))
        REVERSE_INDEXES=$(seq ${LAST_ELEMENT} -1 0)
        for i in $REVERSE_INDEXES; do
            local cmd=${CLEANUP[$i]}
            $cmd
        done
    fi
    echo "done"
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


TEMP=$(getopt -o h --long help,validate,push,packages:,upstream:,debian:,remote: -n 'autopkg.sh' -- "$@")

if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi

eval set -- "$TEMP"

while true ; do
  case "$1" in
    -h|--help) usage ;;
    --upstream) LOCALUPSTREAM=$2 ; shift 2 ;;
    --debian) LOCALDEBIAN=$2 ; shift 2 ;;
    --remote) REMOTE=$2 ; shift 2 ;;
    --packages) PKGAREA=$2 ; shift 2 ;;
    --validate) VALIDATE=true ; shift ;;
    --push) PUSH=true ; shift ;;
    --) shift ; break ;;
    *) echo "Internal error!" ; usage ;;
  esac
done

# The root of the git repository, no matter where we're called from
TOPLEVEL="$(git rev-parse --show-toplevel)"

: ${LOCALUPSTREAM:=$(parse_git_branch)}
: ${LOCALDEBIAN:=debian}
: ${REMOTE:=origin}
: ${VALIDATE:=false}
: ${PUSH:=false}

: ${PKGAREA:=~/packages}
: ${BACKUPAREA:=~/backup}

cd "$TOPLEVEL"

# Prerequisites: Test all important directories exist
test -d "$PKGAREA" || die "Package area directory $PKGAREA missing"
test -d "$BACKUPAREA" || die "Backup area directory $BACKUPAREA missing"

# Prerequisite: Test the dialog utility is available
dialog --help &>/dev/null || die "Could not run the 'dialog' utility"

BUILDAREA=$(mktemp -d --tmpdir=/tmp build-area.XXX)
add_cleanup rm -r $BUILDAREA

echo "############################################################################"
echo "Will build packages under $BUILDAREA"
echo "Local upstream branch: $LOCALUPSTREAM"
echo "Local debian branch: $LOCALDEBIAN"
$VALIDATE && echo "Will fetch $REMOTE and check if $LOCALUPSTREAM and $LOCALDEBIAN are up-to-date"
echo "############################################################################"
echo "Press Enter to continue..."
read

MODIFIED=$(git status --short | grep -v "??")
test -z "$MODIFIED" || die "error: Repository is dirty. Commit your local changes:\n $MODIFIED"

set -e
trap cleanup EXIT

add_checkpoint

# Create a temporary debian branch to do everything
TMPDEBIAN=$(mktemp -u debian.XXX)
git branch --track $TMPDEBIAN  $LOCALDEBIAN
add_cleanup git branch -D $TMPDEBIAN

git checkout $TMPDEBIAN
add_cleanup git checkout $LOCALUPSTREAM

# Whether we are in snapshot or release mode
snap=false
mrgextra=-m
dchextra=-R
mrgmsg="Merge branch '$LOCALUPSTREAM' into $LOCALDEBIAN"
dialog --yesno "Create Snapshot?" 5 20 && snap=true  && dchextra=-S && mrgextra= && mrgmsg=

# merge local branch into tmp branch with a nice commit message,
# so it can be pushed as is to upstream debian
export GIT_MERGE_AUTOEDIT=no
git merge $mrgextra ${mrgextra:+"$mrgmsg"} $LOCALUPSTREAM

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

add_cleanup git reset --hard HEAD
# Build all packages
git-buildpackage --git-export-dir="$BUILDAREA" \
                 --git-upstream-branch=$LOCALUPSTREAM \
                 --git-debian-branch=$TMPDEBIAN \
                 --git-export=INDEX \
                 --git-ignore-new -sa

# do some dirty backup
# pkgarea might be needed by auto-deploy tool
rm -f "$PKGAREA"/* || true
cp -v "$BUILDAREA"/* "$PKGAREA"/ || true
cp -v "$BUILDAREA"/* "$BACKUPAREA"/ || true



function check_remote(){

  git fetch $1 2>/dev/null || die "Could not fetch $1"
  git fetch $1 $2 2>/dev/null|| die "Could not fetch $1/$2"

  commits_behind=$(git rev-list $2..$1/$2 | wc -l)
  if [ $commits_behind -ne 0 ]; then
    die "Your local branch is outdated. Please run:\ngit pull --rebase $1/$2"
  fi


}

if $VALIDATE; then
  check_remote $REMOTE $LOCALUPSTREAM
  check_remote $REMOTE $LOCALDEBIAN
fi


  # trap - EXIT
  # here we can push the commits to the remote debian branch as they are
echo
echo "#################################################"
echo "##                  SUCCESS                    ##"
echo "#################################################"
if $PUSH; then
  git push --tags $REMOTE $TMPDEBIAN:$LOCALDEBIAN
  git push $REMOTE $LOCALUPSTREAM:$LOCALUPSTREAM
fi

exit 0
