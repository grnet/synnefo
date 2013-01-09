#!/bin/bash

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

source devtools/autopkg.conf

# The root of the git repository, no matter where we're called from
TOPLEVEL="$(git rev-parse --show-toplevel)"
CURRENT_BRANCH=$(parse_git_branch)

LOCALBRANCH="$CURRENT_BRANCH"
LOCALDEBIAN=$1
DEBIANBRANCH=${LOCALDEBIAN:- origin/$REMOTEDEBIAN}

MODIFIED=$(git status --short | grep -v "??")
if [[ -n $MODIFIED ]]; then
        echo "error: Repository is dirty. Commit your local changes."
        exit 1
fi


set -e
trap cleanup EXIT

cd "$TOPLEVEL"

# Prerequisites: Test all important directories exist
test -d "$PKGAREA" || die "Package area directory $PKGAREA missing"
test -d "$BACKUPAREA" || die "Backup area directory $BACKUPAREA missing"

# Prerequisite: Test the dialog utility is available
dialog --help &>/dev/null || die "Could not run the 'dialog' utility"


echo "##########################################################"
echo "Will build packages"
echo "under '$BUILDAREA',"
echo "from local branch '$LOCALBRANCH'"
echo "and debian branch '$DEBIANBRANCH'"
echo "##########################################################"
echo "Press Enter to continue..."
read

add_checkpoint

# Create a temporary debian branch to do everything
TMPDEBIAN=$(mktemp -u debian.XXX)

git branch --track $TMPDEBIAN  $DEBIANBRANCH
#add_cleanup git branch -D $TMPDEBIAN

git checkout $TMPDEBIAN
add_cleanup git checkout $LOCALBRANCH

add_checkpoint

# Whether we are in snapshot or release mode
snap=false
mrgextra=-m
dchextra=-R
mrgmsg="Merge branch '$REMOTEUPSTREAM' into $REMOTEDEBIAN"
dialog --yesno "Create Snapshot?" 5 20 && snap=true && dchextra=-S && mrgextra= && mrgmsg=

# merge local branch into tmp branch with a nice commit message,
# so it can be pushed as is to upstream debian
GIT_MERGE_AUTOEDIT=no
git merge $mrgextra ${mrgextra:+"$mrgmsg"} $LOCALBRANCH

lo
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
                 --git-upstream-branch=$LOCALBRANCH \
                 --git-debian-branch=$TMPDEBIAN \
                 --git-export=INDEX \
                 --git-ignore-new -sa

# do some dirty backup
# pkgarea might be needed by auto-deploy tool
rm -f "$PKGAREA"/* || true
cp -v "$BUILDAREA"/* "$PKGAREA"/ || true
cp -v "$BUILDAREA"/* "$BACKUPAREA"/ || true

echo "###############################################"
echo "####              SUCCESS                  ####"
echo "###############################################"

git fetch origin
#check if your local branch is up-to-date
commits_behind=$(git rev-list $LOCALBRANCH..origin/$REMOTEUPSTREAM | wc -l)
if [ $commits_behind -ne 0 ]; then
  die "Your local branch is outdated!! Please run: git pull --rebase origin/$REMOTEUPSTREAM"
fi
commits_behind=$(git rev-list $DEBIANBRANCH..origin/$REMOTEDEBIAN | wc -l)
if [ $commits_behind -ne 0 ]; then
  die "Your debian branch is outdated!! Please run: git pull --rebase origin/$REMOTEDEBIAN"
fi

trap - EXIT

# Remove the added versions.py files
git reset --hard HEAD
# here we can push the commits to the remote debian branch as they are

if ! $snap; then
  TAGS="--tags"
fi
echo "git push $TAGS origin $TMPDEBIAN:$REMOTEDEBIAN"
echo "git checkout $LOCALBRANCH"
echo "git push $TAGS origin $LOCALBRANCH:$REMOTEUPSTREAM"
echo

exit 0
