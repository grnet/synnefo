#!/bin/sh
set -e

PACKAGES_DIR=$1

shift

TEMP_DIR=$(mktemp -d /tmp/devflow_autopkg_XXXXXXX)

# Create the packages
devflow-autopkg snapshot -b $TEMP_DIR $@

# MOVE the packages
mkdir -p $PACKAGES_DIR
mv -n $TEMP_DIR/* $PACKAGES_DIR

echo "Moved packages to: $(pwd)/$PACKAGES_DIR"
