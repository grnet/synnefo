#!/bin/sh

set -e

export SYNNEFO_SETTINGS_DIR=/tmp/snf-test-settings

SNF_MANAGE=$(which snf-manage) ||
	echo "Cannot find snf-manage in $PATH" 1>&2 && exit 1

APPS="api db logic plankton quotas vmapi im quotaholder_app helpdesk"
TEST="$SNF_MANAGE test $APPS --traceback --settings=synnefo.settings.test"

if coverage >/dev/null 2>&1; then
  coverage run $TEST
  coverage report --include=snf-*
else
  echo "WARNING: Cannot find coverage in path, skipping coverage tests" 1>&2
  $TEST
fi
