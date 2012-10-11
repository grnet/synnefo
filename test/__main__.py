from os.path import dirname

from kkconfig import run_test_cases
from kkquotaholderapi import KKQuotaHolderAPITest
from limits import LimitsTest
from createrelease import CreateReleaseListAPITest

HERE = dirname(__file__)

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
    run_test_cases(all_cases)
