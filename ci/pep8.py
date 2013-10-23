#!/usr/bin/env python

"""
Check for pep8 error in a list of files

Get a list of files as command line arguments.
Of these files, invoke pep8 only for the ones that
actually exists, their name ends with .py, and doesn't
belong to our exclude list.

"""

import os
import sys


EXCLUDE = [
    "distribute_setup.py",
    "setup.py",
    "rapi.py",
    "dictconfig.py",
    "ordereddict.py",
    "parsedate.py",
]


def filter_files(files):
    """Filter our non-useful files

    We want to keep only python files (ending with .py),
    that actually exists and are not in our exclude list
    """

    # Remove duplicated file names
    files = list(set(files))

    py_files = []
    for f in files:
        # Check if file is a python file
        if not f.endswith(".py"):
            continue
        #Check if file is to be excluded
        if os.path.basename(f) in EXCLUDE:
            continue
        # Check if file existsw
        if not os.path.isfile(f):
            continue
        # Append file name
        py_files.append(f)

    return py_files


def run_pep8(files):
    """Invoke pep8

    Return the exit code

    """
    if files:
        print "Invoke pep8 for the following files:\n  %s\n\n" \
            % "\n  ".join(files)
        return os.system("pep8 %s" % " ".join(files))
    else:
        print "No files to check.. aborting"
        return 0


def main():
    """Our main program

    Read command line arguments.
    Filter out non-useful files.
    Invoke pep8.

    """
    files = sys.argv[1:]
    py_files = filter_files(files)
    exit_code = run_pep8(py_files)
    if exit_code != 0:
        status = "exit with status %s" % exit_code
        sys.exit(status)


if __name__ == "__main__":
    main()
