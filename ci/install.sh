#!/bin/sh

if [ -n "$VIRTUAL_ENV" ]; then
  OPTIONS=--script-dir=$VIRTUAL_ENV/bin/
  echo $OPTIONS
else
  OPTIONS=
fi

set -e
cwd=`dirname $0`
cd "$cwd"/..

. ./ci/config

# Update version
devflow-update-version

for project in $PROJECTS; do
  cd $project
  python setup.py develop -N $OPTIONS
  cd -
done
