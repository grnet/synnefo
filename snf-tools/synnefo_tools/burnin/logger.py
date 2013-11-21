# Copyright 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

"""
This is the logging class for burnin

It supports logging both for the stdout/stderr as well as file logging at the
same time.

The stdout/stderr logger supports verbose levels and colors but the file
logging doesn't (we use the info verbose level for our file logger).

Our loggers have primitive support for handling parallel execution (even though
burnin doesn't support it yet). To do so the stdout/stderr logger prepends the
name of the test under execution to every line it prints. On the other hand the
file logger waits to lock the file, then reads it, prints the message to the
corresponding line and closes the file.


"""

import os
import sys
import os.path
import datetime

from synnefo_tools.burnin import filelocker


# --------------------------------------------------------------------
# Constant variables
LOCK_EXT = ".lock"
SECTION_SEPARATOR = \
    "-- -------------------------------------------------------------------"
SECTION_PREFIX = "-- "
SECTION_RUNNED = "Tests Runned"
SECTION_RESULTS = "Results"
SECTION_NEW = "__ADD_NEW_SECTION__"
SECTION_PASSED = "  * Passed:"
SECTION_FAILED = "  * Failed:"


# --------------------------------------------------------------------
# Helper functions
def _blue(msg):
    """Blue color"""
    return "\x1b[1;34m" + str(msg) + "\x1b[0m"


def _yellow(msg):
    """Yellow color"""
    return "\x1b[33m" + str(msg) + "\x1b[0m"


def _red(msg):
    """Yellow color"""
    return "\x1b[31m" + str(msg) + "\x1b[0m"


def _magenta(msg):
    """Magenta color"""
    return "\x1b[35m" + str(msg) + "\x1b[0m"


def _green(msg):
    """Green color"""
    return "\x1b[32m" + str(msg) + "\x1b[0m"


def _format_message(msg, *args):
    """Format the message using the args"""
    if args:
        return (msg % args) + "\n"
    else:
        return msg + "\n"


def _list_to_string(lst, append=""):
    """Convert a list of strings to string

    Append the value given in L{append} in front of all lines
    (except of the first line).

    """
    if isinstance(lst, list):
        return append.join(lst).rstrip('\n')
    else:
        return lst.rstrip('\n')


# --------------------------------------
def _locate_sections(contents):
    """Locate the sections inside the logging file"""
    i = 0
    res = []
    for cnt in contents:
        if SECTION_SEPARATOR in cnt:
            res.append(i+1)
        i += 1
    return res


def _locate_input(contents, section):
    """Locate position to insert text

    Given a section location the next possition to insert text inside that
    section.

    """
    sect_locs = _locate_sections(contents)
    if section == SECTION_NEW:
        # We want to add a new section
        # Just return the position of SECTION_RESULTS
        for obj in sect_locs:
            if SECTION_RESULTS in contents[obj]:
                return obj - 1
    else:
        # We will add our message in this location
        for (index, obj) in enumerate(sect_locs):
            if section in contents[obj]:
                return sect_locs[index+1] - 3

    # We didn't find our section??
    sys.stderr.write("Section %s could not be found in logging file\n"
                     % section)
    sys.exit("Error in logger._locate_input")


def _add_testsuite_results(contents, section, testsuite):
    """Add the given testsuite to results

    Well we know that SECTION_FAILED is the last line and SECTION_PASSED is the
    line before, so we are going to cheat here and use this information.

    """
    if section == SECTION_PASSED:
        line = contents[-2]
        new_line = line.rstrip() + " " + testsuite + ",\n"
        contents[-2] = new_line
    elif section == SECTION_FAILED:
        line = contents[-1]
        new_line = line.rstrip() + " " + testsuite + ",\n"
        contents[-1] = new_line
    else:
        sys.stderr.write("Unknown section %s in _add_testsuite_results\n"
                         % section)
        sys.exit("Error in logger._add_testsuite_results")
    return contents


def _write_log_file(file_location, section, message):
    """Write something to our log file

    For this we have to get the lock, read and parse the file add the new
    message and re-write the file.

    """
    # Get the lock
    file_lock = os.path.splitext(file_location)[0] + LOCK_EXT
    with filelocker.lock(file_lock, filelocker.LOCK_EX):
        with open(file_location, "r+") as log_file:
            contents = log_file.readlines()
            if section == SECTION_PASSED or section == SECTION_FAILED:
                # Add testsuite to results
                new_contents = \
                    _add_testsuite_results(contents, section, message)
            else:
                # Add message to its line
                input_loc = _locate_input(contents, section)
                new_contents = \
                    contents[:input_loc] + [message] + contents[input_loc:]
            log_file.seek(0)
            log_file.write("".join(new_contents))


# --------------------------------------------------------------------
# The Log class
class Log(object):
    """Burnin logger

    """
    # ----------------------------------
    # Too many arguments. pylint: disable-msg=R0913
    def __init__(self, output_dir, verbose=1, use_colors=True,
                 in_parallel=False, quiet=False, curr_time=None):
        """Initialize our loggers

        The file to be used by our file logger will be created inside
        the L{output_dir} with name the current timestamp.

        @type output_dir: string
        @param output_dir: the directory to save the output file
        @type verbose: int
        @param verbose: the verbose level to use for stdout/stderr logger
            0: verbose at minimum level (only which test we are running now)
            1: verbose at info level (information about our running test)
            2: verbose at debug level
        @type use_colors: boolean
        @param use_colors: use colors for out stdout/stderr logger
        @type in_parallel: boolean
        @param in_parallel: this signifies that burnin is running in parallel
        @type quiet: boolean
        @type quiet: do not print logs to stdout/stderr

        """
        self.verbose = verbose
        self.use_colors = use_colors
        self.in_parallel = in_parallel
        self.quiet = quiet

        assert output_dir

        # Create file for logging
        output_dir = os.path.expanduser(output_dir)
        if not os.path.exists(output_dir):
            self.debug(None, "Creating directory %s", output_dir)
            try:
                os.makedirs(output_dir)
            except OSError as err:
                msg = ("Failed to create folder \"%s\" with error: %s\n"
                       % (output_dir, err))
                sys.stderr.write(msg)
                sys.exit("Failed to create log folder")

        if curr_time is None:
            curr_time = datetime.datetime.now()
        timestamp = datetime.datetime.strftime(
            curr_time, "%Y%m%d%H%M%S (%a %b %d %Y %H:%M)")
        file_name = timestamp + ".log"
        self.file_location = os.path.join(output_dir, file_name)

        self._write_to_stdout(None, "Starting burnin with id %s\n" % timestamp)

        # Create the logging file
        self._create_logging_file(timestamp)

    def _create_logging_file(self, timestamp):
        """Create the logging file"""
        self.debug(None, "Using \"%s\" file for logging", self.file_location)
        with open(self.file_location, 'w') as out_file:
            out_file.write(SECTION_SEPARATOR + "\n")
            out_file.write("%s%s (%s):\n\n\n\n" %
                           (SECTION_PREFIX, SECTION_RUNNED, timestamp))
            out_file.write(SECTION_SEPARATOR + "\n")
            out_file.write("%s%s:\n\n" % (SECTION_PREFIX, SECTION_RESULTS))
            out_file.write(SECTION_PASSED + "\n" + SECTION_FAILED + "\n")

    def __del__(self):
        """Delete the Log object"""
        # Remove the lock file
        if hasattr(self, "file_location"):
            file_lock = os.path.splitext(self.file_location)[0] + LOCK_EXT
            try:
                os.remove(file_lock)
            except OSError:
                self.debug(None, "Couldn't delete lock file")

    def print_logfile_to_stdout(self):
        """Print the contents of our log file to stdout"""
        with open(self.file_location, 'r') as fin:
            sys.stdout.write(fin.read())

    # ----------------------------------
    # Logging methods
    def debug(self, section, msg, *args):
        """Debug messages (verbose 2)

        We show debug messages only to stdout. The message will be formatted
        using the args.

        """
        msg = "  (DD) " + _list_to_string(msg, append="       ")
        if self.verbose >= 2:
            colored_msg = self._color_message(None, msg, *args)
            self._write_to_stdout(section, colored_msg)

    def log(self, section, msg, *args):
        """Normal messages (verbose 0)"""
        assert section, "Section can not be empty"

        msg = _list_to_string(msg)

        colored_msg = self._color_message(None, msg, *args)
        self._write_to_stdout(section, colored_msg)

        plain_msg = _format_message(msg, *args)
        self._write_to_file(section, plain_msg)

    def info(self, section, msg, *args):
        """Info messages (verbose 1)

        Prepare message and write it to file logger and stdout logger

        """
        assert section, "Section can not be empty"

        msg = "  " + _list_to_string(msg, "  ")
        if self.verbose >= 1:
            colored_msg = self._color_message(None, msg, *args)
            self._write_to_stdout(section, colored_msg)

        plain_msg = _format_message(msg, *args)
        self._write_to_file(section, plain_msg)

    def warning(self, section, msg, *args):
        """Warning messages"""
        assert section, "Section can not be empty"

        msg = "  (WW) " + _list_to_string(msg, "       ")

        colored_msg = self._color_message(_yellow, msg, *args)
        self._write_to_stderr(section, colored_msg)

        plain_msg = _format_message(msg, *args)
        self._write_to_file(section, plain_msg)

    def error(self, section, msg, *args):
        """Error messages"""
        assert section, "Section can not be empty"

        msg = "  (EE) " + _list_to_string(msg, "       ")

        colored_msg = self._color_message(_red, msg, *args)
        self._write_to_stderr(section, colored_msg)

        plain_msg = _format_message(msg, *args)
        self._write_to_file(section, plain_msg)

    def _write_to_stdout(self, section, msg):
        """Write to stdout"""
        if not self.quiet:
            if section is not None and self.in_parallel:
                sys.stdout.write(section + ": " + msg)
            else:
                sys.stdout.write(msg)

    def _write_to_stderr(self, section, msg):
        """Write to stderr"""
        if not self.quiet:
            if section is not None and self.in_parallel:
                sys.stderr.write(section + ": " + msg)
            else:
                sys.stderr.write(msg)

    def _write_to_file(self, section, msg):
        """Write to file"""
        _write_log_file(self.file_location, section, msg)

    # ----------------------------------
    # Handle testsuites
    def testsuite_start(self, testsuite):
        """Start a new testsuite

        Add a new section in the logging file

        """
        assert testsuite, "Testsuite name can not be emtpy"

        # Add a new section in the logging file
        test_runned = "  * " + testsuite + "\n"
        _write_log_file(self.file_location, SECTION_RUNNED, test_runned)

        new_section_entry = \
            SECTION_SEPARATOR + "\n" + SECTION_PREFIX + testsuite + "\n\n\n\n"
        _write_log_file(self.file_location, SECTION_NEW, new_section_entry)

        # Add new section to the stdout
        msg = "Starting testsuite %s" % testsuite
        colored_msg = self._color_message(_magenta, msg)
        self._write_to_stdout(None, colored_msg)

    def testsuite_success(self, testsuite):
        """A testsuite has successfully finished

        Update Results

        """
        assert testsuite, "Testsuite name can not be emtpy"

        # Add our testsuite to Results
        _write_log_file(self.file_location, SECTION_PASSED, testsuite)

        # Add success to stdout
        msg = "Testsuite %s passed" % testsuite
        colored_msg = self._color_message(_green, msg)
        self._write_to_stdout(None, colored_msg)

    def testsuite_failure(self, testsuite):
        """A testsuite has failed

        Update Results

        """
        assert testsuite, "Testsuite name can not be emtpy"

        # Add our testsuite to Results
        _write_log_file(self.file_location, SECTION_FAILED, testsuite)

        # Add success to stdout
        msg = "Testsuite %s failed" % testsuite
        colored_msg = self._color_message(_red, msg)
        self._write_to_stdout(None, colored_msg)

    # ----------------------------------
    # Colors
    def _color_message(self, color_fun, msg, *args):
        """Color a message before printing it

        The color_fun parameter is used when we want the whole message to be
        colored.

        """
        if self.use_colors:
            if callable(color_fun):
                if args:
                    return color_fun((msg % args)) + "\n"
                else:
                    return color_fun(msg) + "\n"
            else:
                args = tuple([_blue(arg) for arg in args])
                return _format_message(msg, *args)
        else:
            return _format_message(msg, *args)
