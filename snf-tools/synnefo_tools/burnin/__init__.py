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
from synnefo_tools.burnin.stale_tests import \
    StaleServersTestSuite, StaleNetworksTestSuite


# --------------------------------------------------------------------
# Define our TestSuites
TESTSUITES = [
    AstakosTestSuite,
    FlavorsTestSuite,
    ImagesTestSuite,
    PithosTestSuite,
    ServerTestSuite,
    NetworkTestSuite,
]
TSUITES_NAMES = [tsuite.__name__ for tsuite in TESTSUITES]

STALE_TESTSUITES = [
    # Must be runned in this order
    StaleServersTestSuite,
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

    # Used * or ** magic. pylint: disable-msg=W0142
    parser = optparse.OptionParser(**kwargs)
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
        type="int", default=300, dest="action_timeout", metavar="TIMEOUT",
        help="Wait TIMEOUT seconds for a server action to complete, "
             "then the test is considered failed")
    parser.add_option(
        "--action-warning", action="store",
        type="int", default=120, dest="action_warning", metavar="TIMEOUT",
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
             "\"name:user_name\" or \"id:uuuid\")")
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
        help="Turn off log output")
    parser.add_option(
        "--final-report-only", action="store_true",
        default=False, dest="final_report",
        help="Turn off log output and only print the contents of the log "
             "file at the end of the test. Useful when burnin is used in "
             "script files and it's output is to be sent using email")

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

    # `quiet' implies not `final_report'
    if opts.quiet:
        opts.final_report = False
    # `final_report' implies `quiet'
    if opts.final_report:
        opts.quiet = True

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
    return common.run_burnin(testsuites, failfast=failfast,
                             final_report=opts.final_report)


if __name__ == "__main__":
    sys.exit(main())
