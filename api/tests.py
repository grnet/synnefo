#
# Unit Tests for api
#
# Provides automated tests for db module
#
# Copyright 2010 Greek Research and Technology Network
#

from django.test import TestCase
from django.test.client import Client
import json
from synnefo.db.models import VirtualMachine

class APITestCase(TestCase):
    fixtures = [ 'api_test_data' ]

    def setUp(self):
        pass

    def testAPIVersion(self):
        """ check if the v1.0 version of the rackspace cloud servers API is provided
        """
        c = Client()
        response = c.get('/api/v1.0/')
        # Check that the response is 200 OK.
        self.assertEqual(response.status_code, 200)
        expected = '{\n    "version": {\n        "status": "CURRENT", \n        "wadl": "http://docs.rackspacecloud.com/servers/api/v1.0/application.wadl", \n        "docURL": "http://docs.rackspacecloud.com/servers/api/v1.0/cs-devguide-20090714.pdf ", \n        "id": "v1.0"\n    }\n}'
        self.assertEqual(response.content, expected)
    
    def testServerList(self):
        """ test if the expected list of servers is returned by the API
        """        
        c = Client()
        response = c.get('/api/v1.0/servers/detail')
        vms_from_api = json.loads(response.content)['servers']
        vms_from_db = VirtualMachine.objects.all()
        self.assertEqual(len(vms_from_api), len(vms_from_db))
