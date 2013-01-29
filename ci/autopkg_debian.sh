#!/usr/bin/env sh

BUILD_NUMBER=$1
BUILDBOT_BUILD_DIR=buildpkg_debian

shift

TEMP_DIR=$(mktemp -d /tmp/devflow_autopkg_XXXXXXX)

# Create the packages
devflow-autopkg snapshot -b $TEMP_DIR $@

# MOVE the packages
mkdir -p buildpkg_debian/$BUILD_NUMBER
mv -n $TEMP_DIR/* $BUILDBOT_BUILD_DIR/$BUILD_NUMBER/

echo "Moved packages to: $(pwd)/$BUILDBOT_BUILD_DIR/$BUILD_NUMBER"
