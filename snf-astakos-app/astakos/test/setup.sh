#!/bin/bash

d=`dirname $0`
export SYNNEFO_SETTINGS_DIR=$d/settings
snf-manage syncdb --noinput
snf-manage migrate
snf-manage flush --noinput

HOST=127.0.0.1
P1=8000
P2=8008

pkill -f "runserver $HOST:$P1"
pkill -f "runserver $HOST:$P2"

snf-manage runserver $HOST:$P1 &
snf-manage runserver $HOST:$P2 &

while true; do
    nc -z -w 4 $HOST $P1
    OUT=$?
    if [ $OUT -eq 0 ]
    then
        nc -z -w 4 $HOST $P2
        OUT=$?
        if [ $OUT -eq 0 ]
        then break
        else sleep 0.1
        fi
    else sleep 0.1
    fi
done

snf-manage astakos-load-service-resources
