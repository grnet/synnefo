#! /bin/bash

#Print the details for testcases that failed the last 30 minutes. 
#Usage: ./snf-burnin-details.sh LOG_FOLDER

path=$1
flag=0
curr=$(date -d "30 minutes ago" +%Y%m%d%H%M%S)
for dir in `find ${path} -maxdepth 1 -type d -cmin -60`; do

    if [ x"$dir" == "x${path}" ]; then
	continue
    fi
    for file in $dir/*/detail* ; do

	x=`dirname $file`
	y=`dirname $x`
	d=`basename $y`

	if (($d<$curr)); then
	    if grep -E "(ERROR)|(FAILED)" "$file" >/dev/null; then
		cat "$file"
		flag=1
	    fi
	fi
    done
done
exit

if [ $flag -ge 1 ]; then 
    exit 1
else
    exit 0
fi
