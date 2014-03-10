#!/bin/bash


# --------------------------------------------------------------------
# Configure script parameters

# ----------------------------------------
# Here we define the tokens for each user burnin will
# test along with an alias for each token.
# For each user define an ALIAS, his TOKEN, an IMAGEID and a FLAVOR.
USERS=(
    "burnin1" "token to be used"
    "name:Image name (reg expr)" "name:Flavor name (reg expr)"

    "burnin2" "token to be used"
    "name:Image name (reg expr)" "name:Flavor name (reg expr)"

    "burnin3" "token to be used"
    "name:Image name (reg expr)" "name:Flavor name (reg expr)"
  )

# ----------------------------------------
# Here we define the email parameters
# Email Tag
TAG="[synnefo.org-burnin]"
# Email Recipients
RECIPIENTS="burnin@synnefo.org"
# Subject for a successful burnin run
# (will be "$TAG ($ALIAS) $SUCCESS_SUBJECT" for each burnin instance)
SUCCESS_SUBJECT="Burnin Succeeded"
# Subject for a failed burnin run
# (will be "$TAG ($ALIAS) $FAILURE_SUBJECT" for each burnin instance)
FAILURE_SUBJECT="Burnin Failed"

# ----------------------------------------
# Some burnin parameters
AUTH_URL="https://accounts.synnefo.org/identity/v2.0"

# ----------------------------------------
# Burnin executable and log files
Burnin="snf-burnin"
# Log Folder will be $LOGFOLDER/$ALIAS for each burnin instance
LOGFOLDER="/var/log/burnin/"
# Lock file (we don't want two instances of this script)
LOCKFILE="/tmp/burnin.lockfile"


# --------------------------------------------------------------------
# Script functions

run_burnin() {
    local alias="$1"
    local token="$2"
    local image="$3"
    local flavor="$4"
    local success_subject="$TAG ($alias) $SUCCESS_SUBJECT"
    local failure_subject="$TAG ($alias) $FAILURE_SUBJECT"
    local logfolder="$LOGFOLDER/$alias"
    local error_summary
    local stale_subject

    # Check for stale servers/networks
    $Burnin --token="$token" --auth-url="$AUTH_URL" --show-stale --quiet
    if [ $? -eq 0 ]; then
        # No stale servers/networks found. Run burnin
        results=$($Burnin \
            --token="$token" \
            --auth-url="$AUTH_URL" \
            --images="$image" \
            --flavors="$flavor" \
            --log-folder="$logfolder" \
            --final-report-only \
            2>&1)

        if [ $? -ne 0 ]; then
            # Burnin failed
            # Send email
            error_summary=$(echo "$results" | \
                sed -n 's/  \* Failed: \(.*\)/\1/p')
            echo "$results" | /usr/bin/mailx -E \
                -s "$failure_subject: $error_summary" $RECIPIENTS
#        else
#            echo "$results" | /usr/bin/mailx -E \
#                -s "$success_subject" $RECIPIENTS
        fi
    else
        # Burnin found stale servers/networks. Try to clean them
        results=$($Burnin --token="$token" --auth-url="$AUTH_URL" \
            --delete-stale --log-folder="$logfolder" --final-report-only 2>&1)
        if [ $? -ne 0 ]; then
            stale_subject="$failure_subject: Couldn't delete stale servers/networks"
        else
            stale_subject="$success_subject: Stale servers/networks deleted"
        fi

        # Send mail
        echo "$results" | /usr/bin/mailx -E \
            -s "$stale_subject" $RECIPIENTS
    fi
}


# --------------------------------------------------------------------
# For each user run burnin function

(
    flock -xn 200 || exit 1

    set "${USERS[@]}"

    while [ -n "$1" ]; do
        run_burnin "$1" "$2" "$3" "$4" &
        shift 4
    done

    wait
) 200>$LOCKFILE
