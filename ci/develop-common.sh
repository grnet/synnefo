#!/bin/sh

if [ -n "$VIRTUAL_ENV" ]; then
  OPTIONS=--script-dir=$VIRTUAL_ENV/bin/
  echo $OPTIONS
else
  OPTIONS=
fi

. ./ci/config
