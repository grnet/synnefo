#!/usr/bin/env sh

set -e

TEST="$(which snf-manage) test api db logic plankton vmapi im helpdesk --settings=synnefo.settings.test"

if coverage >/dev/null 2>&1; then
  coverage run $TEST
  coverage report --include=snf-*
else
  echo "coverage not installed"
  $TEST
fi
