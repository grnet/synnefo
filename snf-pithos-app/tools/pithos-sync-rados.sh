#!/bin/bash
# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


DRYRUN="n"
INFO="n"
QUIET="n"
DEEP="n"
RADOS_POOL=""
PITHOS_DIR=""

function check_file
{
        obj=$(basename $1)
        cmd="rados -p $RADOS_POOL stat $obj 2>/dev/null"
        rados_size=$(rados -p $RADOS_POOL stat $obj 2>/dev/null | awk '{print $5}')
        if [ ! -z "$rados_size" ] ; then
                file_size=$(stat --format %s $1)
                if [ ! $rados_size -eq $file_size ] ; then
                        maybe_echo "$obj size mismatch (RADOS: $rados_size vs
					FILE: $file_size"
			cmd_put="rados -p $RADOS_POOL put $obj $1"
			maybe_info "$cmd_put"
			maybe_eval "$cmd_put"
		else
			if [ $DEEP != "n" ] ; then
				tmpfile="$obj""_tmp"
				cmd_get="rados -p $RADOS_POOL get $obj $tmpfile > /dev/null 2>&1"
				maybe_info "$cmd_get"
				eval "$cmd_get"
				diff -s "$1" $tmpfile 2>&1 > /dev/null
				if [ ! $? -eq 0 ] ; then
					maybe_echo "$obj data mismatch (file $1)"
					cmd_put="rados -p $RADOS_POOL put $obj $1"
					maybe_info "$cmd_put"
					maybe_eval "$cmd_put"
				fi
				rm $tmpfile
			fi
                fi
        else
                maybe_echo "$obj missing"
		ch=$(stat --format %z $1)
		maybe_echo "File last change in $ch"
                cmd_put="rados -p $RADOS_POOL put $obj $1"
		maybe_echo "$cmd_put"
		maybe_eval "$cmd_put"
        fi
}
export -f check_file

function maybe_echo
{
	if [ $QUIET != "y" ] ; then
		echo "$1"
	fi
}
export -f maybe_echo

function maybe_info
{
	if [ $INFO == "y" ] ; then
		maybe_echo "$1"
	fi
}
export -f maybe_info

function maybe_eval
{
	if [ $DRYRUN != "y" ] ; then
		cmd="$1"
		if [ $QUIET == "y" ] ; then
			cmd="$cmd"" > /dev/null"
		fi
		eval "$cmd"
	fi
}
export -f maybe_eval

args=`getopt -o iqnp:d: -l info,quiet,deep,dryrun,pool:,directory: -n $0 -- "$@"`

if [ ! $? -eq 0 ]; then
	echo "get opt error"
	exit 1
fi

eval set -- "$args"


while /bin/true; do
	case $1 in
		-i|--info)
			INFO="y" ; shift ;;
		-q|--quiet)
			QUIET="y"; shift ;;
		-p|--pool)
			RADOS_POOL="$2"; shift 2 ;;
		-d|--directory)
			PITHOS_DIR="$2"; shift 2 ;;
		--deep)
			DEEP="y"; shift ;;
		-n|--dryrun)
			DRYRUN="y"; shift ;;
		--)
			shift; break ;;
	esac
done

if [ -z "$RADOS_POOL" ] ; then
	maybe_echo "RADOS pool (-p | --pool) must be provided"
	exit 1;
fi

rados lspools | grep "$RADOS_POOL" 2>&1 > /dev/null
if [ ! $? -eq 0 ] ; then
	maybe_echo "RADOS pool must be a valid pool"
	exit 1;
fi

if [ -z "$PITHOS_DIR" ] ; then
	maybe_echo "Pithos directory (-d | --directory) must be provided"
	exit 1;
fi

if [ ! -d "$PITHOS_DIR" ] ; then
	maybe_echo "Pithos directory must be valid"
	exit 1;
fi

export INFO
export QUIET
export DEEP
export DRYRUN
export RADOS_POOL
export PITHOS_DIR

find $PITHOS_DIR -type f -print0 | parallel -0 --max-procs 30 check_file "{}"
