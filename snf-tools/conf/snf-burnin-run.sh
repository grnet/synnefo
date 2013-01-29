#!/bin/bash

#Example script for an snf-burnin cronjob.
#Starts an a snf-burnin test, deletes stale instances and archives old logs.
#It aborts if snf-burnin runs for longer than expected.

#Usage: ./snf-burnin-run.sh

API=""
PLANKTON=""
PLANKTON_USER=""
TOKEN=""
IMAGEID=""
OUTPUT=""

# Delete previously stalled objects.
snf-burnin --api=$API --token=$TOKEN --delete-stale

# Run burnin for 25 minutes. Fail after that.
timeout --foreground 25m \
    snf-burnin --api=$API \
               --plankton=$PLANKTON \
               --plankton-user=$PLANKTON_USER \
               --token=$TOKEN \
               --image-id=$IMAGEID \
               --action-timeout 120 \
               --log-folder=$OUTPUT \
               --nofailfast

# Delete possibly stalled objects.
snf-burnin --api=$API --token=$TOKEN --delete-stale

#Delete old folders
old=$(date -d "1 week ago" +%Y%m%d%H%M%S)
for dir in $OUTPUT/* ; do
    d=`basename $dir`
    (($d<$old)) && rm -r "$dir"
done
