#!/bin/sh

# Files to be excluded from pep8 tests
EXCLUDE=migrations,build,setup,distribute_setup.py,\
setup.py,rapi.py,dictconfig.py,ordereddict.py

if [ $# -eq 0 ]; then
    echo "No files to be tested"
else
    pep8 --exclude=$EXCLUDE "$@"
fi
