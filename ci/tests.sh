#!/bin/sh
set -e

SNF_MANAGE=$(which snf-manage) ||
	{ echo "Cannot find snf-manage in $PATH" 1>&2; exit 1; }

runtest () {
    TEST="$SNF_MANAGE test $* --traceback --settings=synnefo.settings.test"

    if coverage >/dev/null 2>&1; then
      coverage run $TEST
      coverage report --include=snf-*
    else
      echo "WARNING: Cannot find coverage in path, skipping coverage tests" 1>&2
      $TEST
    fi
}

export SYNNEFO_SETTINGS_DIR=/tmp/snf-test-settings

ASTAKOS_APPS="im quotaholder_app"
CYCLADES_APPS="api db logic plankton quotas vmapi helpdesk"
PITHOS_APPS="api"

TEST_COMPONENTS="$@"
if [ -z "$TEST_COMPONENTS" ]; then
    TEST_COMPONENTS="astakos cyclades pithos"
fi

for component in $TEST_COMPONENTS; do
    if [ "$component" = "astakos" ]; then
        runtest $ASTAKOS_APPS
    elif [ "$component" = "cyclades" ]; then
        export SYNNEFO_EXCLUDE_PACKAGES="snf-pithos-app"
        runtest $CYCLADES_APPS
    elif [ "$component" = "pithos" ]; then
        export SYNNEFO_EXCLUDE_PACKAGES="snf-cyclades-app"
        runtest $PITHOS_APPS
    fi
done
