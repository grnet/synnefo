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

from logger import Log


# --------------------------------------------------------------------
# Global variables
logger = None  # Invalid constant name. pylint: disable-msg=C0103
AUTH_URL = "https://accounts.okeanos.grnet.gr/identity/v2.0/"
TOKEN = ""
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
        # Access to a protected member. pylint: disable-msg=W0212
        logger.log(test.__class__.__name__, test._testMethodDoc)

    # Method could be a function. pylint: disable-msg=R0201
    def _test_failed(self, test, err):
        """Test failed"""
        # Access to a protected member. pylint: disable-msg=W0212
        err_msg = test._testMethodDoc + "... failed."
        logger.error(test.__class__.__name__, err_msg)
        (err_type, err_value, err_trace) = err
        trcback = traceback.format_exception(err_type, err_value, err_trace)
        logger.info(test.__class__.__name__, trcback)

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
# Too many public methods (45/20). pylint: disable-msg=R0904
class BurninTests(unittest.TestCase):
    """Common class that all burnin tests should implement"""
    @classmethod
    def setUpClass(cls):  # noqa
        """Initialize BurninTests"""
        cls.suite_name = cls.__name__
        cls.connection_retry_limit = CONNECTION_RETRY_LIMIT
        logger.testsuite_start(cls.suite_name)

        # Set test parameters
        cls.longMessage = True

    def test_clients_setup(self):
        """Initializing astakos/cyclades/pithos clients"""
        # Update class attributes
        cls = type(self)
        self.info("Astakos auth url is %s", AUTH_URL)
        cls.astakos = AstakosClient(AUTH_URL, TOKEN)
        cls.astakos.CONNECTION_RETRY_LIMIT = CONNECTION_RETRY_LIMIT

        cls.compute_url = \
            cls.astakos.get_service_endpoints('compute')['publicURL']
        self.info("Cyclades url is %s", cls.compute_url)
        cls.compute = ComputeClient(cls.compute_url, TOKEN)
        cls.compute.CONNECTION_RETRY_LIMIT = CONNECTION_RETRY_LIMIT

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


# --------------------------------------------------------------------
# Helper functions
def was_succesful(tsuite, success):
    """Handle whether a testsuite was succesful or not"""
    if success:
        logger.testsuite_success(tsuite)
    else:
        logger.testsuite_failure(tsuite)


def setup_logger(output_dir, verbose=1, use_colors=True, in_parallel=False):
    """Setup our logger"""
    global logger  # Using global statement. pylint: disable-msg=C0103,W0603

    logger = Log(output_dir, verbose=verbose,
                 use_colors=use_colors, in_parallel=in_parallel)
