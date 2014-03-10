#!/bin/bash

d=`dirname $0`
export SYNNEFO_SETTINGS_DIR=$d/settings

HOST=127.0.0.1
P=8000

pkill -f "runserver"

snf-manage runserver $HOST:$P &> server.$P.out &

while true; do
    nc -z -w 4 $HOST $P
    OUT=$?
    if [ $OUT -eq 0 ]
    then break
    else sleep 0.1
    fi
done
