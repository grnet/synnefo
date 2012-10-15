### IMPORTS ###
import sys
import os
# The following import is copied from snf-tools/syneffo_tools/burnin.py
# Thank you John Giannelos <johngian@grnet.gr>
# Use backported unittest functionality if Python < 2.7
try:
    import unittest2 as unittest
except ImportError:
    if sys.version_info < (2, 7):
        raise Exception("The unittest2 package is required for Python < 2.7")
    import unittest

from commissioning.clients.http import HTTP_API_Client
from commissioning import QuotaholderAPI
import random 

### DEFS ###
def new_quota_holder_client():
    """
    Create a new quota holder api client
    """
    class QuotaholderHTTP(HTTP_API_Client):
        api_spec = QuotaholderAPI()

    global QH_URL
    return QuotaholderHTTP(QH_URL)

def run_test_case(test_case):
    """
    Runs the test_case and returns the result
    """
    # Again from snf-tools/synnefo_tools/burnin.py
    # Thank you John Giannelos <johngian@grnet.gr>
    printf("Running {0}", test_case)
    import sys
    suite = unittest.TestLoader().loadTestsFromTestCase(test_case)
    runner = unittest.TextTestRunner(stream = sys.stderr, verbosity = 2, failfast = True, buffer = False)
    return runner.run(suite)

def run_test_cases(test_cases):
    for test_case in test_cases:
        run_test_case(test_case)

def rand_string():
   alphabet = 'abcdefghijklmnopqrstuvwxyz'
   min = 5
   max = 15
   string=''
   for x in random.sample(alphabet,random.randint(min,max)):
    string += x
   return string

def environ_get(key, default_value = ''):
    if os.environ.has_key(key):
        return os.environ.get(key)
    else:
        return default_value

def printf(fmt, *args):
    print(fmt.format(*args))

### CLASSES ###
class QHTestCase(unittest.TestCase):
    def setUp(self):
        self.qh = new_quota_holder_client()

    def tearDown(self):
        del self.qh


### VARS ###
DefaultOrCustom = {
    True: "default",
    False: "custom"
}

# Use environ vars [TEST_]QH_{HOST, PORT}
QH_HOST = environ_get("TEST_QH_HOST", environ_get("QH_HOST", "127.0.0.1"))
QH_PORT = environ_get("TEST_QH_PORT", environ_get("QH_PORT", "8008"))

assert QH_HOST != None
assert QH_PORT != None

printf("Will connect to QH_HOST = {0}", QH_HOST)
printf("            and QH_PORT = {0}", QH_PORT)

QH_URL = "http://{0}:{1}/api/quotaholder/v".format(QH_HOST, QH_PORT)
