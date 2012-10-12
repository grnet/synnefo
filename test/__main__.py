from sys import argv,executable
from os.path import dirname
from config import run_test_cases
from config import printf
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

printf("=======================================================")
printf("Using {0} {1}", executable, ' '.join(argv))
printf("Running tests from {0}", HERE)
printf("=======================================================")
printf("All tests are:")
for test_case in all_cases:
    printf("  {0}", test_case.__name__)
run_test_cases(all_cases)
printf("=======================================================")
printf("")