# Copyright 2012 GRNET S.A. All rights reserved.
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

### IMPORTS ###
import sys
import os
import subprocess
import time
from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, error as socket_error
from errno import ECONNREFUSED
from os.path import dirname

# The following import is copied from snf-tools/syneffo_tools/burnin.py
# Thank you John Giannelos <johngian@grnet.gr>
# Use backported unittest functionality if Python < 2.7
try:
    import unittest2 as unittest
except ImportError:
    if sys.version_info < (2, 7):
        raise Exception("The unittest2 package is required for Python < 2.7")
    import unittest

from kamaki.clients.quotaholder import QuotaholderClient
from synnefo.lib.quotaholder.api import (InvalidKeyError, NoEntityError,
                                         NoQuantityError, NoCapacityError,
                                         ExportLimitError, ImportLimitError)

import random 

def printf(fmt, *args):
    print(fmt.format(*args))

def environ_get(key, default_value = ''):
    if os.environ.has_key(key):
        return os.environ.get(key)
    else:
        return default_value

# Use environ vars [TEST_]QH_{HOST, PORT}
QH_HOST = environ_get("TEST_QH_HOST", environ_get("QH_HOST", "127.0.0.1"))
QH_PORT = environ_get("TEST_QH_PORT", environ_get("QH_PORT", "8008"))

assert QH_HOST != None
assert QH_PORT != None

printf("Will connect to QH_HOST = {0}", QH_HOST)
printf("            and QH_PORT = {0}", QH_PORT)

QH_SERVER = '{0}:{1}'.format(QH_HOST, QH_PORT)
QH_URL = "http://{0}/api/quotaholder/v".format(QH_SERVER)

### DEFS ###
def new_quota_holder_client():
    """
    Create a new quota holder api client
    """
    return QuotaholderClient(QH_URL)

def run_test_case(test_case):
    """
    Runs the test_case and returns the result
    """
    # Again from snf-tools/synnefo_tools/burnin.py
    # Thank you John Giannelos <johngian@grnet.gr>
    printf("Running {0}", test_case)
    import sys
    suite = unittest.TestLoader().loadTestsFromTestCase(test_case)
    runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=2,
                                     failfast=True, buffer=False)
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

HERE = dirname(__file__)

def init_server():
    p = subprocess.Popen(['setsid', HERE+'/qh_init', QH_SERVER])
    s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
    while True:
        try:
            s.connect((QH_HOST, int(QH_PORT)))
            break
        except socket_error, e:
            if e.errno != ECONNREFUSED:
                raise
            time.sleep(0.1)
    return p.pid

### CLASSES ###
class QHTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.server = init_server()
        self.qh = new_quota_holder_client()
#        self.qh.create_entity(create_entity=[("pgerakios", "system", "key1", "")])

    def setUp(self):
        print

    @classmethod
    def tearDownClass(self):
        from signal import SIGTERM
        os.kill(-self.server, SIGTERM)
        os.remove('/tmp/qh_testdb')
        del self.qh


### VARS ###
DefaultOrCustom = {
    True: "default",
    False: "custom"
}

