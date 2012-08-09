#! /bin/bash

#Example script to check current status. 
#Checks for testcases that failed the last 30 minutes in a given folder.
 
#Usage: ./check-burnin-output.sh LOG_FOLDER

curr=$(date -d "30 minutes ago" +%Y%m%d%H%M%S)
for dir in ${1}/* ; do
    d=`basename $dir`
    if (($d>$curr)); then
	if find "$dir"/* -type f -size +0 | grep failed >/dev/null; then
	    echo snf-burnin encountered a testcase failure. See log for details...
	    exit 1
	fi
	echo No testcase failure encountered...
	exit 0
    fi
done