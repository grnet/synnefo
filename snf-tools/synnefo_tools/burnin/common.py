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
Common utils for burnin tests

"""

import sys
import datetime
import traceback
# Use backported unittest functionality if Python < 2.7
try:
    import unittest2 as unittest
except ImportError:
    if sys.version_info < (2, 7):
        raise Exception("The unittest2 package is required for Python < 2.7")
    import unittest

from kamaki.clients.astakos import AstakosClient
from kamaki.clients.compute import ComputeClient
from kamaki.clients.pithos import PithosClient

from synnefo_tools.burnin.logger import Log


# --------------------------------------------------------------------
# Global variables
logger = None  # Invalid constant name. pylint: disable-msg=C0103
SNF_TEST_PREFIX = "snf-test-"
CONNECTION_RETRY_LIMIT = 2


# --------------------------------------------------------------------
# BurninTestResult class
class BurninTestResult(unittest.TestResult):
    """Modify the TextTestResult class"""
    def __init__(self):
        super(BurninTestResult, self).__init__()

        # Test parameters
        self.failfast = True

    def startTest(self, test):  # noqa
        """Called when the test case test is about to be run"""
        super(BurninTestResult, self).startTest(test)
        logger.log(test.__class__.__name__, test.shortDescription())

    # Method could be a function. pylint: disable-msg=R0201
    def _test_failed(self, test, err):
        """Test failed"""
        # Get class name
        if test.__class__.__name__ == "_ErrorHolder":
            class_name = test.id().split('.')[-1].rstrip(')')
        else:
            class_name = test.__class__.__name__
        err_msg = str(test) + "... failed (%s)."
        timestamp = datetime.datetime.strftime(
            datetime.datetime.now(), "%a %b %d %Y %H:%M:%S")
        logger.error(class_name, err_msg, timestamp)
        (err_type, err_value, err_trace) = err
        trcback = traceback.format_exception(err_type, err_value, err_trace)
        logger.info(class_name, trcback)

    def addError(self, test, err):  # noqa
        """Called when the test case test raises an unexpected exception"""
        super(BurninTestResult, self).addError(test, err)
        self._test_failed(test, err)

    def addFailure(self, test, err):  # noqa
        """Called when the test case test signals a failure"""
        super(BurninTestResult, self).addFailure(test, err)
        self._test_failed(test, err)


# --------------------------------------------------------------------
# BurninTests class
# Too few public methods (0/2). pylint: disable-msg=R0903
class Clients(object):
    """Our kamaki clients"""
    auth_url = None
    token = None
    # Astakos
    astakos = None
    retry = CONNECTION_RETRY_LIMIT
    # Compute
    compute = None
    compute_url = None
    # Cyclades
    cyclades = None
    # Pithos
    pithos = None
    pithos_url = None


# Too many public methods (45/20). pylint: disable-msg=R0904
class BurninTests(unittest.TestCase):
    """Common class that all burnin tests should implement"""
    clients = Clients()
    run_id = None
    use_ipv6 = None
    action_timeout = None
    action_warning = None
    query_interval = None

    @classmethod
    def setUpClass(cls):  # noqa
        """Initialize BurninTests"""
        cls.suite_name = cls.__name__
        logger.testsuite_start(cls.suite_name)

        # Set test parameters
        cls.longMessage = True

    def _setattr(self, attr, value):
        """Used by tests to set an attribute to TestCase

        Since each instance of the TestCase will only be used to run a single
        test method (a new fixture is created for each test) the attributes can
        not be saved in the class instance. Instead the class itself should be
        used.

        """
        setattr(self.__class__, attr, value)

    def test_000_clients_setup(self):
        """Initializing astakos/cyclades/pithos clients"""
        # Update class attributes
        self.info("Astakos auth url is %s", self.clients.auth_url)
        self.clients.astakos = AstakosClient(
            self.clients.auth_url, self.clients.token)
        self.clients.astakos.CONNECTION_RETRY_LIMIT = self.clients.retry

        self.clients.compute_url = \
            self.clients.astakos.get_service_endpoints('compute')['publicURL']
        self.info("Cyclades url is %s", self.clients.compute_url)
        self.clients.compute = ComputeClient(
            self.clients.compute_url, self.clients.token)
        self.clients.compute.CONNECTION_RETRY_LIMIT = self.clients.retry

        self.clients.pithos_url = self.clients.astakos.\
            get_service_endpoints('object-store')['publicURL']
        self.info("Pithos url is %s", self.clients.pithos_url)
        self.clients.pithos = PithosClient(
            self.clients.pithos_url, self.clients.token)
        self.clients.pithos.CONNECTION_RETRY_LIMIT = self.clients.retry

    # ----------------------------------
    # Loggers helper functions
    def log(self, msg, *args):
        """Pass the section value to logger"""
        logger.log(self.suite_name, msg, *args)

    def info(self, msg, *args):
        """Pass the section value to logger"""
        logger.info(self.suite_name, msg, *args)

    def debug(self, msg, *args):
        """Pass the section value to logger"""
        logger.debug(self.suite_name, msg, *args)

    def warning(self, msg, *args):
        """Pass the section value to logger"""
        logger.warning(self.suite_name, msg, *args)

    def error(self, msg, *args):
        """Pass the section value to logger"""
        logger.error(self.suite_name, msg, *args)

    # ----------------------------------
    # Helper functions that every testsuite may need
    def _get_uuid(self):
        """Get our uuid"""
        authenticate = self.clients.astakos.authenticate()
        uuid = authenticate['access']['user']['id']
        self.info("User's uuid is %s", uuid)
        return uuid

    def _get_username(self):
        """Get our User Name"""
        authenticate = self.clients.astakos.authenticate()
        username = authenticate['access']['user']['name']
        self.info("User's name is %s", username)
        return username

    def _get_list_of_flavors(self, detail=False):
        """Get (detailed) list of flavors"""
        if detail:
            self.info("Getting detailed list of flavors")
        else:
            self.info("Getting simple list of flavors")
        flavors = self.clients.compute.list_flavors(detail=detail)
        return flavors

    def _set_pithos_account(self, account):
        """Set the pithos account"""
        assert account, "No pithos account was given"

        self.info("Setting pithos account to %s", account)
        self.clients.pithos.account = account

    def _get_list_of_containers(self, account=None):
        """Get list of containers"""
        if account is not None:
            self._set_pithos_account(account)
        self.info("Getting list of containers")
        return self.clients.pithos.list_containers()

    def _create_pithos_container(self, container):
        """Create a pithos container

        If the container exists, nothing will happen

        """
        assert container, "No pithos container was given"

        self.info("Creating pithos container %s", container)
        self.clients.pithos.container = container
        self.clients.pithos.container_put()


# --------------------------------------------------------------------
# Initialize Burnin
def initialize(opts, testsuites):
    """Initalize burnin

    Initialize our logger and burnin state

    """
    # Initialize logger
    global logger  # Using global statement. pylint: disable-msg=C0103,W0603
    logger = Log(opts.log_folder, verbose=opts.verbose,
                 use_colors=opts.use_colors, in_parallel=False,
                 quiet=opts.quiet)

    # Initialize clients
    Clients.auth_url = opts.auth_url
    Clients.token = opts.token

    # Pass the rest options to BurninTests
    BurninTests.use_ipv6 = opts.use_ipv6
    BurninTests.action_timeout = opts.action_timeout
    BurninTests.action_warning = opts.action_warning
    BurninTests.query_interval = opts.query_interval
    BurninTests.run_id = SNF_TEST_PREFIX + \
        datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d%H%M%S")

    # Choose tests to run
    if opts.tests != "all":
        testsuites = opts.tests
    if opts.exclude_tests is not None:
        testsuites = [tsuite for tsuite in testsuites
                      if tsuite not in opts.exclude_tests]

    return testsuites


# --------------------------------------------------------------------
# Run Burnin
def run(testsuites, failfast=False, final_report=False):
    """Run burnin testsuites"""
    global logger  # Using global. pylint: disable-msg=C0103,W0603,W0602

    success = True
    for tcase in testsuites:
        tsuite = unittest.TestLoader().loadTestsFromTestCase(tcase)
        results = tsuite.run(BurninTestResult())

        was_success = was_successful(tcase.__name__, results.wasSuccessful())
        success = success and was_success
        if failfast and not success:
            break

    # Are we going to print final report?
    if final_report:
        logger.print_logfile_to_stdout()
    # Clean up our logger
    del(logger)

    # Return
    return 0 if success else 1


# --------------------------------------------------------------------
# Helper functions
def was_successful(tsuite, success):
    """Handle whether a testsuite was succesful or not"""
    if success:
        logger.testsuite_success(tsuite)
        return True
    else:
        logger.testsuite_failure(tsuite)
        return False
