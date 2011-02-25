#
# Unit Tests for api
#
# Provides automated tests for db module
#
# Copyright 2010 Greek Research and Technology Network
#

from django.test import TestCase
from django.test.client import Client

class APITestCase(TestCase):
    def setUp(self):
        pass

    def testAPIVersion(self):
        c = Client()
        response = c.get('/api/v1.0/')
        # Check that the response is 200 OK.
        self.assertEqual(response.status_code, 200)
        expected = '{\n    "version": {\n        "status": "CURRENT", \n        "wadl": "http://docs.rackspacecloud.com/servers/api/v1.0/application.wadl", \n        "docURL": "http://docs.rackspacecloud.com/servers/api/v1.0/cs-devguide-20090714.pdf ", \n        "id": "v1.0"\n    }\n}'
        self.assertEqual(response.content, expected)
    
