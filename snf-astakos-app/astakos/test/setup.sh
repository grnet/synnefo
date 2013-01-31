#!/bin/sh

d=`dirname $0`
export SYNNEFO_SETTINGS_DIR=$d/settings
snf-manage syncdb --noinput
snf-manage migrate
