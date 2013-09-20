#!/bin/bash

# Files to be excluded from pep8 tests
EXCLUDE=migrations,build,setup,distribute_setup.py,\
setup.py,rapi.py,dictconfig.py,ordereddict.py

# Keep only *.py files
py_files=`echo "$@" | awk '/.*\.py/' RS=" "`

if [ -z "$py_files" ]; then
    echo "No files to be tested"
else
    pep8 --exclude=$EXCLUDE "$py_files"
fi
