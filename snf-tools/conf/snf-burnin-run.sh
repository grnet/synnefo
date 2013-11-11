#!/bin/bash


# --------------------------------------------------------------------
# Configure script parameters

# ----------------------------------------
# Here we define the tokens for each user burnin will
# test along with an alias for each token.
# For each user define an ALIAS, his TOKEN, an IMAGEID and a FLAVOR.
USERS=(\
    "burnin1" "token to be used" \
    "image id to be used" "flavor id to be used" \

    "burnin2" "token to be used" \
    "image id to be used" "flavor id to be used" \

    "burnin3" "token to be used" \
    "image id to be used" "flavor id to be used" \
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
SYSTEM_IMAGES_USER="uuid-of-owner-of-system-images"
TIMEOUT=240

# ----------------------------------------
# Burnin executable and log files
Burnin="snf-burnin"
# Log Folder will be $LOGFOLDER/$ALIAS for each burnin instance
LOGFOLDER="/var/log/burnin_results/"
# Output file will be $OUTPUTFOLDER/burnin-$ALIAS.out for each burnin instance
OUTPUTFOLDER="/tmp"
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
    local outputfile="$OUTPUTFOLDER/burnin-$alias.out"
    local failed=false
    local error_summary
    local stale_subject

    # Save date-stamp to output
    date > $outputfile
    echo -e \
        "\n\n===== Burnin Output ========================================" \
        >> $outputfile

    # Check for stale servers/networks
    $Burnin --token="$token" --auth-url="$AUTH_URL" --show-stale 2>&1 | \
        grep "test" >> $outputfile 2>&1
    if [ $? -ne 0 ]; then
        # No stale servers/networks found. Run burnin
        $Burnin --token="$token" \
                --action-timeout="$TIMEOUT" \
                --image-id="$image" \
                --log-folder="$logfolder" \
                --auth-url="$AUTH_URL" \
                --force-flavor="$flavor" \
                --system-images-user="$SYSTEM_IMAGES_USER" \
                --nofailfast \
            &>> $outputfile

        echo -e \
            "\n\n===== Burnin Logs ==========================================" \
            >> $outputfile

        # Search log files for errors
        for file in `ls -1d $logfolder/* | tail -1`/*/detail* ; do
            if egrep "(ERROR)|(FAILED)" $file > /dev/null; then
                failed=true
                echo "FILENAME: $file" >> $outputfile
                echo "ERROR: " >> $outputfile
                cat "$file" >> $outputfile
            fi
        done

        # Clean output file from escape characters
        sed -ri "s/\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?[m|K]//g" $outputfile

        # Send emails
        if $failed; then
            error_summary="`cat $outputfile | \
                egrep "ERROR: test_|FAIL: test_" | \
                awk '{ print $2 }' | grep -v "^$" | \
                sed -e 's/_/ /g' | cut -d" " -f3- | \
                tr '\n' ',' | sed -e 's/,$//g' | \
                sed -e 's/,/,  /g'`"
            cat $outputfile | /usr/bin/mailx -E \
                -s "$failure_subject: $error_summary" $RECIPIENTS
#        else
#            cat $outputfile | /usr/bin/mailx -E \
#                -s "$success_subject" $RECIPIENTS
        fi
    else
        # Burnin found stale servers/networks. Try to clean them
        $Burnin --token="$token" --auth-url="$AUTH_URL" --delete-stale \
            >> $outputfile 2>&1
        if [ $? -ne 0 ]; then
            stale_subject="$failure_subject: Couldn't delete stale servers/networks"
        else
            stale_subject="$success_subject: Stale servers/networks deleted"
        fi

        # Clean output file from escape characters
        sed -ri "s/\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?[m|K]//g" $outputfile

        # Send mail
        cat $outputfile | /usr/bin/mailx -E \
            -s "$stale_subject" $RECIPIENTS
    fi
}


# --------------------------------------------------------------------
# For each user run burnin function

(
    flock -xn 200 || exit 1

    set ${USERS[@]}

    while [ -n "$1" ]; do
        run_burnin "$1" "$2" "$3" "$4" &
        shift 4
    done

    wait
) 200>$LOCKFILE
