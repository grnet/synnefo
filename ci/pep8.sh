#!/bin/sh

# Files to be excluded from pep8 tests
EXCLUDE=migrations,build,setup,distribute_setup.py,\
setup.py,rapi.py,dictconfig.py,ordereddict.py

pep8 --exclude=$EXCLUDE "$@"
