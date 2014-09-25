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

"""
Burnin: functional tests for Synnefo

"""

import sys
import optparse

from synnefo_tools import version
from synnefo_tools.burnin import common
from synnefo_tools.burnin.astakos_tests import AstakosTestSuite
from synnefo_tools.burnin.images_tests import \
    FlavorsTestSuite, ImagesTestSuite
from synnefo_tools.burnin.pithos_tests import PithosTestSuite
from synnefo_tools.burnin.server_tests import ServerTestSuite
from synnefo_tools.burnin.network_tests import NetworkTestSuite
from synnefo_tools.burnin.projects_tests import QuotasTestSuite
from synnefo_tools.burnin.snapshots import SnapshotsTestSuite
from synnefo_tools.burnin.stale_tests import \
    StaleServersTestSuite, StaleFloatingIPsTestSuite, StaleNetworksTestSuite


# --------------------------------------------------------------------
# Define our TestSuites
TESTSUITES = [
    AstakosTestSuite,
    FlavorsTestSuite,
    ImagesTestSuite,
    PithosTestSuite,
    ServerTestSuite,
    NetworkTestSuite,
    QuotasTestSuite,
    SnapshotsTestSuite
]
TSUITES_NAMES = [tsuite.__name__ for tsuite in TESTSUITES]

STALE_TESTSUITES = [
    # Must be runned in this order
    StaleServersTestSuite,
    StaleFloatingIPsTestSuite,
    StaleNetworksTestSuite,
]
STALE_TSUITES_NAMES = [tsuite.__name__ for tsuite in STALE_TESTSUITES]


def string_to_class(names):
    """Convert class namesto class objects"""
    return [eval(name) for name in names]


# --------------------------------------------------------------------
# Parse arguments
def parse_comma(option, _, value, parser):
    """Parse comma separated arguments"""
    parse_input = [p.strip() for p in value.split(',')]
    setattr(parser.values, option.dest, parse_input)


def parse_arguments(args):
    """Parse burnin arguments"""
    kwargs = {}
    kwargs["usage"] = "%prog [options]"
    kwargs["description"] = \
        "%prog runs a number of test scenarios on a Synnefo deployment."

    parser = optparse.OptionParser(**kwargs)  # pylint: disable=star-args
    parser.disable_interspersed_args()

    parser.add_option(
        "--auth-url", action="store",
        type="string", default=None, dest="auth_url",
        help="The AUTH URI to use to reach the Synnefo API")
    parser.add_option(
        "--token", action="store",
        type="string", default=None, dest="token",
        help="The token to use for authentication to the API")
    parser.add_option(
        "--failfast", action="store_true",
        default=False, dest="failfast",
        help="Fail immediately if one of the tests fails")
    parser.add_option(
        "--no-ipv6", action="store_false",
        default=True, dest="use_ipv6",
        help="Disable IPv6 related tests")
    parser.add_option(
        "--action-timeout", action="store",
        type="int", default=420, dest="action_timeout", metavar="TIMEOUT",
        help="Wait TIMEOUT seconds for a server action to complete, "
             "then the test is considered failed")
    parser.add_option(
        "--action-warning", action="store",
        type="int", default=180, dest="action_warning", metavar="TIMEOUT",
        help="Warn if TIMEOUT seconds have passed and a server action "
             "has not been completed yet")
    parser.add_option(
        "--query-interval", action="store",
        type="int", default=3, dest="query_interval", metavar="INTERVAL",
        help="Query server status when requests are pending "
             "every INTERVAL seconds")
    parser.add_option(
        "--flavors", action="callback", callback=parse_comma,
        type="string", default=None, dest="flavors", metavar="FLAVORS",
        help="Force all server creations to use one of the specified FLAVORS "
             "instead of a randomly chosen one. Supports both search by name "
             "(reg expression) with \"name:flavor name\" or by id with "
             "\"id:flavor id\"")
    parser.add_option(
        "--images", action="callback", callback=parse_comma,
        type="string", default=None, dest="images", metavar="IMAGES",
        help="Force all server creations to use one of the specified IMAGES "
             "instead of the default one (a Debian Base image). Just like the "
             "--flavors option, it supports both search by name and id")
    parser.add_option(
        "--system-user", action="store",
        type="string", default=None, dest="system_user",
        help="Owner of system images (typed option in the form of "
             "\"name:user_name\" or \"id:uuid\")")
    parser.add_option(
        "--show-stale", action="store_true",
        default=False, dest="show_stale",
        help="Show stale servers from previous runs. A server is considered "
             "stale if its name starts with `%s'. If stale servers are found, "
             "exit with exit status 1." % common.SNF_TEST_PREFIX)
    parser.add_option(
        "--delete-stale", action="store_true",
        default=False, dest="delete_stale",
        help="Delete stale servers from previous runs")
    parser.add_option(
        "--log-folder", action="store",
        type="string", default="/var/log/burnin/", dest="log_folder",
        help="Define the absolute path where the output log is stored")
    parser.add_option(
        "--verbose", "-v", action="store",
        type="int", default=1, dest="verbose",
        help="Print detailed output messages")
    parser.add_option(
        "--version", action="store_true",
        default=False, dest="show_version",
        help="Show version and exit")
    parser.add_option(
        "--set-tests", action="callback", callback=parse_comma,
        type="string", default="all", dest="tests",
        help="Set comma separated tests for this run. Available tests: %s"
             % ", ".join(TSUITES_NAMES))
    parser.add_option(
        "--exclude-tests", action="callback", callback=parse_comma,
        type="string", default=None, dest="exclude_tests",
        help="Set comma separated tests to be excluded for this run.")
    parser.add_option(
        "--no-colors", action="store_false",
        default=True, dest="use_colors",
        help="Disable colorful output")
    parser.add_option(
        "--quiet", action="store_true",
        default=False, dest="quiet",
        help="Turn off logging (both console and file logging)")
    parser.add_option(
        "--final-report-only", action="store_true",
        default=False, dest="final_report",
        help="Turn off log output and only print the contents of the log "
             "file at the end of the test. Useful when burnin is used in "
             "script files and it's output is to be sent using email")
    parser.add_option(
        "--temp-directory", action="store",
        default="/tmp/", dest="temp_directory",
        help="Directory to use for saving temporary files")
    parser.add_option(
        "--obj-upload-num", action="store",
        type="int", default=2, dest="obj_upload_num",
        help="Set the number of objects to massively be uploaded "
             "(default: 2)")
    parser.add_option(
        "--obj-upload-min-size", action="store",
        type="int", default=10 * common.MB, dest="obj_upload_min_size",
        help="Set the min size of the object to massively be uploaded "
             "(default: 10MB)")
    parser.add_option(
        "--obj-upload-max-size", action="store",
        type="int", default=20 * common.MB, dest="obj_upload_max_size",
        help="Set the max size of the objects to massively be uploaded "
             "(default: 20MB)")

    (opts, args) = parser.parse_args(args)

    # ----------------------------------
    # Verify arguments
    # If `version' is given show version and exit
    if opts.show_version:
        show_version()
        sys.exit(0)

    # `delete_stale' implies `show_stale'
    if opts.delete_stale:
        opts.show_stale = True

    # log_level:
    #  0 -> log to console and file
    #  1 -> log to file and output the results in console
    #  2 -> don't log
    opts.log_level = 0
    if opts.final_report:
        opts.log_level = 1
    if opts.quiet:
        opts.log_level = 2

    # Check `--set-tests' and `--exclude-tests' options
    if opts.tests != "all" and \
            not (set(opts.tests)).issubset(set(TSUITES_NAMES)):
        raise optparse.OptionValueError("The selected set of tests is invalid")
    if opts.exclude_tests is not None and \
            not (set(opts.exclude_tests)).issubset(set(TSUITES_NAMES)):
        raise optparse.OptionValueError("The selected set of tests is invalid")

    # `token' is mandatory
    mandatory_argument(opts.token, "--token")
    # `auth_url' is mandatory
    mandatory_argument(opts.auth_url, "--auth-url")

    return (opts, args)


def show_version():
    """Show burnin's version"""
    sys.stdout.write("Burnin: version %s\n" % version.__version__)


def mandatory_argument(value, arg_name):
    """Check if a mandatory argument is given"""
    if (value is None) or (value == ""):
        sys.stderr.write("The " + arg_name + " argument is mandatory.\n")
        sys.exit("Invalid input")


# --------------------------------------------------------------------
# Burnin main function
def main():
    """Assemble test cases into a test suite, and run it

    IMPORTANT: Tests have dependencies and have to be run in the specified
    order inside a single test case. They communicate through attributes of the
    corresponding TestCase class (shared fixtures). Distinct subclasses of
    TestCase MAY SHARE NO DATA, since they are run in parallel, in distinct
    test runner processes.

    """

    # Parse arguments using `optparse'
    (opts, _) = parse_arguments(sys.argv[1:])

    # Initialize burnin
    (testsuites, failfast) = \
        common.initialize(opts, TSUITES_NAMES, STALE_TSUITES_NAMES)
    testsuites = string_to_class(testsuites)

    # Run burnin
    # The return value denotes the success status
    return common.run_burnin(testsuites, failfast=failfast)


if __name__ == "__main__":
    sys.exit(main())
