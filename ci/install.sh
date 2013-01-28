#!/usr/bin/env sh
. ./ci/config

for project in $PROJECTS; do
  cd $project
  python setup.py develop
  cd -
done
