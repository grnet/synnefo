#!/bin/bash

umask 022

cwd=`dirname $0`
cd "$cwd"

rm -rf ./build

#if which python2.6; then
#	python2.6 ./setup.py install
#fi

#if which python2.7; then
#	python2.7 ./setup.py install
#fi

python ./setup.py install
