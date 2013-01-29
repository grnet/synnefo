#!/usr/bin/env sh
. ./ci/config

for project in $PROJECTS; do
  pylint --ignore=migrations --ignore=build $project/synnefo
done
