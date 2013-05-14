#!/usr/bin/env sh

set -e

APPS="api db logic plankton quotas vmapi im quotaholder_app helpdesk"
TEST="$(which snf-manage) test $APPS --settings=synnefo.settings.test"

if coverage >/dev/null 2>&1; then
  coverage run $TEST
  coverage report --include=snf-*
else
  echo "coverage not installed"
  $TEST
fi
