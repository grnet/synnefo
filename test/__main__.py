from sys import argv,executable
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

print("=======================================================")
print("Using {0} {1}".format(executable, ' '.join(argv)))
print("Running tests from {0}".format(HERE))
print("=======================================================")
print("All tests are:")
for test_case in all_cases:
    print("  {0}".format(test_case.__name__))
run_test_cases(all_cases)
print("=======================================================")
print("")