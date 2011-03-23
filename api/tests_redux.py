#
# Copyright (c) 2010 Greek Research and Technology Network
#

from django.test import TestCase
from django.test.client import Client

import json

API = 'v1.1redux'


class APIReduxTestCase(TestCase):
    fixtures = [ 'api_redux_test_data' ]
    
    def setUp(self):
        self.client = Client()
        self.server_id = 0
    
    def create_server_name(self):
        self.server_id += 1
        return 'server%d' % self.server_id
    
    def test_create_server_json(self):
        TEMPLATE = '''
        {
            "server" : {
                "name" : "%(name)s",
                "flavorRef" : "%(flavorRef)s",
                "imageRef" : "%(imageRef)s"
            }
        }
        '''
        
        def new_server(imageRef=1, flavorRef=1):
            name = self.create_server_name()
            return name, TEMPLATE % dict(name=name, imageRef=imageRef, flavorRef=flavorRef)
        
        def verify_response(response, name):
            assert response.status_code == 202
            reply =  json.loads(response.content)
            server = reply['server']
            assert server['name'] == name
            assert server['imageRef'] == 1
            assert server['flavorRef'] == 1
            assert server['status'] == 'BUILD'
            assert server['adminPass']
            assert server['addresses']
        
        def verify_error(response, code, name):
            assert response.status_code == code
            reply =  json.loads(response.content)
            assert name in reply
            assert reply[name]['code'] == code
        
        name, data = new_server()
        url = '/api/%s/servers' % API
        response = self.client.post(url, content_type='application/json', data=data)
        verify_response(response, name)
        
        name, data = new_server()
        url = '/api/%s/servers.json' % API
        response = self.client.post(url, content_type='application/json', data=data)
        verify_response(response, name)
        
        name, data = new_server()
        url = '/api/%s/servers.json' % API
        response = self.client.post(url, content_type='application/json', data=data,
                                    HTTP_ACCEPT='application/xml')
        verify_response(response, name)
        
        name, data = new_server(imageRef=0)
        url = '/api/%s/servers' % API
        response = self.client.post(url, content_type='application/json', data=data)
        verify_error(response, 404, 'itemNotFound')
        
        name, data = new_server(flavorRef=0)
        url = '/api/%s/servers' % API
        response = self.client.post(url, content_type='application/json', data=data)
        verify_error(response, 404, 'itemNotFound')
        
        url = '/api/%s/servers' % API
        response = self.client.post(url, content_type='application/json', data='INVALID')
        verify_error(response, 400, 'badRequest')
