#!/usr/bin/python
from commissioning.clients.http import main, HTTP_API_Client
from commissioning import QuotaholderAPI
import unittest
import ConfigParser


class QuotaholderHTTP(HTTP_API_Client):
    api_spec = QuotaholderAPI()

class Config():
    def __init__(self):
        config = ConfigParser.RawConfigParser()
        read_ok = config.read("apitest.cfg")
        if not read_ok:
            pass # raise something?
        self.qh_url = config.get('global', 'QH_URL')
        self.qh = QuotaholderHTTP(self.qh_url)


    def module_config(mod):
        '''Loads the config residing next to the module.'''
        import shlex, os.path
        cp = ConfigParser.RawConfigParser()
        # ''' open(os.path.splitext(mod.__file__)[0] + '.conf')'''
        cp.read_file("test.cfg")
        return cp

class SimpleAPICall(unittest.TestCase):
    def setUp(self):
#        print 'In setUp()'
#        self.fixture = range(1, 10)
#        QH_URL='http://localhost:8008/api/quotaholder/v'
#        self.conf = module_config(__name__ + ".cfg")
#        self.qh = QuotaholderHTTP(QH_URL)
        config = Config()
        self.qh = config.qh
        print self.qh

    def tearDown(self):
#        print 'In tearDown()'
        del self.qh

    def test_001_create_entity(self):
        rejected = self.qh.create_entity(context={},create_entity=[("pgerakios","system","key1","")])
        self.assertEqual(rejected,[])

    def test_002_set_entity_key(self):
        pass

    def test_003_list_entities(self):
        pass

    def test_004_get_entity(self):
        pass

    def test_005_get_limits(self):
        pass

    def test_006_set_limits(self):
        pass

    def test_007_get_holding(self):
        pass

    def test_008_set_holding(self):
        pass

    def test_009_list_resources(self):
        pass

    def test_010_get_quota(self):
        pass

    def test_011_set_quota(self):
        pass

    def test_012_issue_commission(self):
        pass

    def test_013_accept_commission(self):
        pass

    def test_014_reject_commission(self):
        pass

    def test_015_get_pending_commissions(self):
        pass

    def test_016_resolve_pending_commissions(self):
        pass

    def test_017_release_entity(self):
        pass

    def test_018_get_timeline(self):
        pass



if __name__ == "__main__":
    unittest.main()
