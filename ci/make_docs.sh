#!/usr/bin/env sh
set -e

BUILD_DIR=$1
BUILD_NUMBER=$2
DOCS_DIR=$1/$2

cd docs
make html
cd -

mkdir -p $DOCS_DIR
mv -n docs/_build/html/* $DOCS_DIR

echo "Moved docs to to: $(pwd)/$DOCS_DIR"
