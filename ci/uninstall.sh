#!/bin/sh

# `cd` to the top dir of synnefo repository
set -e
cwd=`dirname $0`
cd "$cwd"/..

# Do common tasks for install/uninstall purposes
. ./ci/develop-common.sh

for project in $PROJECTS; do
  cd $project
  python setup.py develop --uninstall $OPTIONS
  cd -
done

for pkg in $DEV_PACKAGES; do
    pip uninstall -y $pkg
done
