#! /bin/bash

#Example script for an snf-burnin cronjob.
#Starts an a snf-burnin test, deletes stale instances and archives old logs.
#It aborts if snf-burnin runs for longer than expected.

#Usage: ./snf-burnin-run.sh TOKEN IMAGE-ID LOG-FOLDER

timeout --foreground 25m snf-burnin --token="$1" --image-id="$2" --action-timeout 120 --log-folder "$3"
snf-burnin --token="$1" --delete-stale

#Delete old folders
old=$(date -d "1 week ago" +%Y%m%d%H%M%S)
for dir in ${3}/* ; do
    d=`basename $dir`
    (($d<$old)) && rm -r "$dir"
done
