#!/bin/sh
set -e

runAstakosTests () {
    if [ -z "$astakos_tests" ]; then return; fi

    export SYNNEFO_EXCLUDE_PACKAGES="snf-cyclades-app"
    CURRENT_COMPONENT=astakos
    createSnfManageTest $astakos_tests
    runTest
}

runCycladesTests () {
    if [ -z "$cyclades_tests" ]; then return; fi

    export SYNNEFO_EXCLUDE_PACKAGES="snf-pithos-app snf-astakos-app"
    CURRENT_COMPONENT=synnefo
    createSnfManageTest $cyclades_tests
    runTest
}

runPithosTests () {
    if [ -z "$pithos_tests" ]; then return; fi

    export SYNNEFO_EXCLUDE_PACKAGES="snf-cyclades-app"
    CURRENT_COMPONENT=pithos
    createSnfManageTest $pithos_tests
    runTest
}

runAstakosclientTests () {
    if [ -z "$astakosclient_tests" ]; then return; fi

    CURRENT_COMPONENT=astakosclient
    for test in $astakosclient_tests; do
        createNoseTest $test
        runTest
    done
}

createSnfManageTest () {
    TEST="$SNF_MANAGE test $* --traceback --noinput --settings=synnefo.settings.test"
}

createNoseTest () {
    TEST="$NOSE $*"
}

runTest () {
    if [ $COVERAGE_EXISTS ]; then
        runCoverage "$TEST"
    else
        # Stop here, if we are on dry run
        if [ $DRY_RUN ]; then
            echo "$TEST"
            return
        fi

        eval $TEST
    fi
}

runCoverage () {
    # Stop here, if we are on dry run
    if [ $DRY_RUN ]; then
        echo "coverage run $1"
        return
    fi

    coverage erase
    coverage run $1
    coverage report --include="*${CURRENT_COMPONENT}*"
}

usage(){
    echo "$1: Wrong input."
    echo "    Usage: $0 [--dry-run] component[.test]"
    exit
}

# Append a string to a given variable.
#
# Arguments: $1: the variable name
#            $2: the string
# Note, the variable must be passed by name, so we need to resort to a bit
# complicated parameter expansions
append () {
    eval $(echo "$1=\"\$${1}\"\" \"\"$2\"")
}

# Check if a string contains a substring
#
# Arguments: $1: The string
#            $2: The substring
contains () {
    case "$1" in
        *$2*) return 0;;  # True
        *) return 1;;     # False
    esac
}

# Get a list of tests for a given component.
#
# Arguments: $1: a component to extract tests from or a single component test
# Returns:   $(astakos/cyclades/pithos/ac)_tests,
#            a list with apps to be tested for each component
extract_tests () {
    # Check all components:
        # If the given component matches one of the components:
            # If total match, return all the tests of the component.
        # Else, if its form matches "component.test", extract only the
        # test.
    # Anything else is considered wrong input

    for c in $ALL_COMPONENTS; do
        if contains $1 $c; then
            if [ "$1" = "$c" ]; then
                append "${c}_tests" "$(eval "echo \$"${c}"_all_tests")"
                return
            elif contains $1 "$c."; then
                append "${c}_tests" $(echo $1 | sed -e 's/[a-z]*\.//g')
                return
            fi
        fi
    done

    usage $1
}

export SYNNEFO_SETTINGS_DIR=/tmp/snf-test-settings

astakos_all_tests="im quotaholder_app oa2"
cyclades_all_tests="api db logic plankton quotas vmapi helpdesk userdata volume"
pithos_all_tests="api"
astakosclient_all_tests="astakosclient"
ALL_COMPONENTS="astakos cyclades pithos astakosclient"

astakos_tests=""
cyclades_tests=""
pithos_tests=""
astakosclient_tests=""

if [ "$1" = "--dry-run" ]; then
    DRY_RUN=0
    shift
fi

TEST_COMPONENTS="$@"
if [ -z "$TEST_COMPONENTS" ]; then
    TEST_COMPONENTS=$ALL_COMPONENTS
fi

# Check if coverage and snf-manage exist
if command -v coverage >/dev/null 2>&1; then
    COVERAGE_EXISTS=0
fi
SNF_MANAGE=$(which snf-manage) ||
    { echo "Cannot find snf-manage in $PATH" 1>&2; exit 1; }
NOSE=$(which nosetests) ||
    { echo "Cannot find nosetests in $PATH" 1>&2; exit 1; }


# Extract tests from a component
for component in $TEST_COMPONENTS; do
    extract_tests $component
done

echo "|===============|============================"
echo "| Component     | Tests"
echo "|---------------|----------------------------"
echo "| Astakos       | $astakos_tests"
echo "| Cyclades      | $cyclades_tests"
echo "| Pithos        | $pithos_tests"
echo "| Astakosclient | $astakosclient_tests"
echo "|===============|============================"
echo ""

if [ ! $COVERAGE_EXISTS ]; then
    echo "WARNING: Cannot find coverage in path." >&2
    echo ""
fi

# For each component, run the specified tests.
runAstakosTests
runCycladesTests
runPithosTests
runAstakosclientTests
