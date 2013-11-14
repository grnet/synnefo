"""Test"""
import unittest

import common
from astakos_tests import AstakosTestCase, AstakosFoo


# --------------------------------------
# Define our TESTSUITE
TESTSUITE = [AstakosTestCase, AstakosFoo]


def test():
    """Test"""
    common.setup_logger("./", verbose=2)

    for tcase in TESTSUITE:
        tsuite = unittest.TestLoader().loadTestsFromTestCase(tcase)
        results = tsuite.run(common.BurninTestResult())
        common.was_succesful(tcase.__name__,
                             results.wasSuccessful())

if __name__ == "__main__":
    test()
