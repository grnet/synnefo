#!/usr/bin/env sh
. ./ci/config

EXCLUDE=migrations,build,setup,distribute_setup.py,setup.py,rapi.py,dictconfig.py,\
ordereddict.py

for project in $PROJECTS; do
  pep8 --exclude=$EXCLUDE $project
done
