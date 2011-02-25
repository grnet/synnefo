#
# Unit Tests for api
#
# Provides automated tests for db module
#
# Copyright 2010 Greek Research and Technology Network
#

from django.test import TestCase
from django.test.client import Client
import simplejson as json
from synnefo.db.models import VirtualMachine

class APITestCase(TestCase):
    fixtures = [ 'api_test_data' ]

    def setUp(self):
        self.client = Client()

    def testAPIVersion(self):
        """ check if the v1.0 version of the rackspace cloud servers API is provided
        """
        response = self.client.get('/api/v1.0/')
        # Check that the response is 200 OK.
        self.assertEqual(response.status_code, 200)
        expected = '{\n    "version": {\n        "status": "CURRENT", \n        "wadl": "http://docs.rackspacecloud.com/servers/api/v1.0/application.wadl", \n        "docURL": "http://docs.rackspacecloud.com/servers/api/v1.0/cs-devguide-20090714.pdf ", \n        "id": "v1.0"\n    }\n}'
        self.assertEqual(response.content, expected)
    
    def testServerList(self):
        """ test if the expected list of servers is returned by the API
        """        
        response = self.client.get('/api/v1.0/servers')
        vms_from_api = json.loads(response.content)['servers']
        vms_from_db = VirtualMachine.objects.all()
        self.assertEqual(len(vms_from_api), len(vms_from_db))
        self.assertTrue(response.status_code in [200,203])

    def testCreateServerEmpty(self):
        """ test if the create server call returns a 400 badRequest if no
            attributes are specified
        """
        response = self.client.post('/api/v1.0/servers',{})
        self.assertEqual(response.status_code, 400)
                                    
    def testCreateServer(self):
        """ test if the create server call returns the expected response if a valid request has been speficied
        """
        request = {
                            'server': {
                                'name'          : 'new-server-test',
                                "imageId"       : 1,
                                "flavorId"      : 1,
                                "metadata"      : {
                                    "My Server Name": "Apache1",
                                },
                                "personality"   : [],
                            }
        }
        response = self.client.post('/api/v1.0/servers', request)
        self.assertEqual(response.status_code, 200)
        #TODO: check response.content


        
