#!/bin/sh

d=`dirname $0`
export SYNNEFO_SETTINGS_DIR=$d/settings
snf-manage astakos-load-service-resources
snf-manage user-add --active test@synnefo.org Tester Tester
snf-manage user-add --active test2@synnefo.org Tester2 Tester2
