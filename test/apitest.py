#!/usr/bin/python
from commissioning.clients.http import main, HTTP_API_Client
from commissioning import QuotaholderAPI
import unittest
import ConfigParser


class QuotaholderHTTP(HTTP_API_Client):
    api_spec = QuotaholderAPI()

class Config():
    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        self.cp.read_file("test.cfg")

    def module_config(mod):
        '''Loads the config residing next to the module.'''
        import shlex, os.path
        cp = ConfigParser.RawConfigParser()
        # ''' open(os.path.splitext(mod.__file__)[0] + '.conf')'''
        cp.read_file("test.cfg")
        return cp

class SimpleAPICall(unittest.TestCase):
    def setUp(self):
        print 'In setUp()'
        self.fixture = range(1, 10)
        QH_URL='http://localhost:8008/api/quotaholder/v'
        self.conf = module_config(__name__ + ".cfg")
        self.qh = QuotaholderHTTP(QH_URL)

    def tearDown(self):
        print 'In tearDown()'
        del self.qh

    def testCreate(self):
        rejected = self.qh.create_entity(context={},create_entity=[("pgerakios","system","key1","")])
        self.assertEqual(rejected,[])

if __name__ == "__main__":
    unittest.main()
