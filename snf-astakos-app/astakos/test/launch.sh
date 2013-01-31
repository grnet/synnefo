#!/bin/bash

cwd=`dirname $0`
cd "$cwd"

export SYNNEFO_SETTINGS_DIR=./settings
HOST=127.0.0.1

pkill -f "runserver $HOST:8000"
pkill -f "runserver $HOST:8008"

snf-manage runserver $HOST:8000 &
snf-manage runserver $HOST:8008 &
