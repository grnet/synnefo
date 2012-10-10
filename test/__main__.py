import os
import sys
from kkquotaholderapi import KKQuotaHolderAPITest
from limits import LimitsTest
from createrelease import CreateReleaseListAPITest 

# The following trick is from from snf-tools/synnefo_tools/burnin.py:
# Use backported unittest functionality if Python < 2.7
try:
    import unittest2 as unittest
except ImportError:
    if sys.version_info < (2, 7):
        raise Exception("The unittest2 package is required for Python < 2.7")
    import unittest

HERE = os.path.dirname(__file__)

# Enumerate all test cases to run.
# In the command line use
#   $ python test
# to run them all

all_cases = [
    CreateReleaseListAPITest,
    KKQuotaHolderAPITest,
    LimitsTest
]

if __name__ == "__main__":
    print("Running tests from {0}".format(HERE))
    print("All tests are: {0}".format(all_cases))
    for test_case in all_cases:
        print("Executing {0}".format(test_case))
        # Again from snf-tools/synnefo_tools/burnin.py
        # Thank you John Giannelos <johngian@grnet.gr>
        suite = unittest.TestLoader().loadTestsFromTestCase(test_case)
        runner = unittest.TextTestRunner(stream = sys.stderr, verbosity = 2, failfast = True, buffer = False)
        result = runner.run(suite)
