#!/bin/sh
set -e

SNF_MANAGE=$(which snf-manage) ||
	{ echo "Cannot find snf-manage in $PATH" 1>&2; exit 1; }

runTest () {
    TEST="$SNF_MANAGE test $* --traceback --noinput --settings=synnefo.settings.test"

    runCoverage "$TEST"
}

runCoverage () {
    if coverage >/dev/null 2>&1; then
      coverage run $1
      coverage report --include=snf-*
    else
      echo "WARNING: Cannot find coverage in path, skipping coverage tests" 1>&2
      $1
    fi
}

export SYNNEFO_SETTINGS_DIR=/tmp/snf-test-settings

ASTAKOS_APPS="im quotaholder_app"
CYCLADES_APPS="api db logic plankton quotas vmapi helpdesk userdata"
PITHOS_APPS="api"

TEST_COMPONENTS="$@"
if [ -z "$TEST_COMPONENTS" ]; then
    TEST_COMPONENTS="astakos cyclades pithos astakosclient"
fi

for component in $TEST_COMPONENTS; do
    if [ "$component" = "astakos" ]; then
        runTest $ASTAKOS_APPS
    elif [ "$component" = "cyclades" ]; then
        export SYNNEFO_EXCLUDE_PACKAGES="snf-pithos-app"
        runTest $CYCLADES_APPS
    elif [ "$component" = "pithos" ]; then
        export SYNNEFO_EXCLUDE_PACKAGES="snf-cyclades-app"
        runTest $PITHOS_APPS
    elif [ "$component" = "astakosclient" ]; then
        TEST="nosetests astakosclient"
        runCoverage "$TEST"
    fi
done
