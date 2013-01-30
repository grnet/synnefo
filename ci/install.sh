#!/usr/bin/env sh

set -e
. ./ci/config

for project in $PROJECTS; do
  cd $project
  python setup.py develop
  cd -
done
