#!/bin/bash

if [ $# -ne 3 ]; then
  echo "$0 localbranch remotedebian remoteupstream"
  exit 1
fi


LOCALBRANCH=$1
REMOTEDEBIAN=$2
REMOTEUPSTREAM=$3
BUILDAREA=~/build-area
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

test -d $BUILDAREA
test -d $PKGAREA
test -d $BACKUPAREA



#TODO: check for up-to-date branches
git checkout $LOCALBRANCH
git checkout $REMOTEUPSTREAM
git checkout $REMOTEDEBIAN

TMPDEBIAN=$(mktemp -u debian.XXX)


# create tmp debian branch to do everything
git checkout --track $REMOTEDEBIAN -b $TMPDEBIAN

mrgextra=-m
mrgmsg="Merge branch '$REMOTEUPSTREAM' into $REMOTEDEBIAN"
dchextra=-R

# whether we are in snapshot or release mode
snap=false

tcdialog --defaultno --yesno "Create Snapshot?" 5 20 && snap=true && dchextra=-S && mrgextra= && mrgmsg=


# merge local branch to tmp branch with correct msg so that it can be pushes as is to upstream debian
git merge --no-edit $mrgextra ${mrgextra:+"$mrgmsg"} $LOCALBRANCH


# auto edit changlog depending on Snapshot or Release mode
export EDITOR=/usr/bin/vim
git-dch --debian-branch=$TMPDEBIAN --git-author --ignore-regex=".*" --multimaint-merge --since=HEAD $dchextra
git add debian/changelog


# get version from the changelog
# we tag here in order sdist to work as expexted.
version=$(IFS="()" ; read  x v x < debian/changelog  ; echo $v)
if ! $snap; then
  git commit -s -a -m "Bump new upstream version"
  TAGFILE=$(mktemp -t tag.XXX)
  tcdialog --inputbox "New Debian Tag: " 5 30 "debian/$version" 2>$TAGFILE
  git tag $(<$TAGFILE)
fi

rm -rf $BUILDAREA/*

for p in $PACKAGES; do

  cd  $p
  python setup.py sdist
  grep "__version_vcs" -r . -l -I | xargs git add -f
  cd -

done


git-buildpackage --git-export-dir=$BUILDAREA \
                 --git-upstream-branch=$REMOTEUPSTREAM \
                 --git-debian-branch=$TMPDEBIAN \
                 --git-export=INDEX \
                 --git-ignore-new -sa

# do some dirty backup
# pkgarea might be needed by auto-deploy tool
rm -f $PKGAREA/* || true
cp -v $BUILDAREA/*deb $PKGAREA/ || true

cp -v $BUILDAREA/* $BACKUPAREA/ || true


git reset --hard HEAD
if $snap ; then
  git checkout $LOCALBRANCH
  git branch -D $TMPDEBIAN
else
  # here we can push as is the commits in remote debian branch
  echo "########### All OK #####################"
  echo "git push origin $REMOTEDEBIAN"
  echo "git checkout $LOCALBRANCH"
  echo
  echo "############ Revert ######################"
  echo "git tag -d " $(<$TAGFILE)
  rm $TAGFILE
fi


