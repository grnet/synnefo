#!/bin/bash

d=`dirname $0`
export SYNNEFO_SETTINGS_DIR=$d/settings
snf-manage syncdb --noinput
snf-manage migrate

HOST=127.0.0.1:8000

snf-manage component-add astakos --base-url $HOST/astakos
snf-manage component-add cyclades --base-url $HOST/cyclades
snf-manage component-add pithos --base-url $HOST/pithos

snf-service-export astakos $HOST/astakos | snf-manage service-import --json -
snf-service-export cyclades $HOST/cyclades | snf-manage service-import --json -
snf-service-export pithos $HOST/pithos | snf-manage service-import --json -
snf-manage resource-modify astakos.pending_app --limit 2
