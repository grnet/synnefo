#
# Unit Tests for api
#
# Provides automated tests for api module
#
# Copyright 2011 Greek Research and Technology Network
#

from django.test import TestCase
from django.test.client import Client

class AuthTestCase(TestCase):
    fixtures = ['auth_test_data']
    apibase = '/api/v1.0'

    

    def setUp(self):
        self.client = Client()

    def register_sibbolleth_user(self):
        """ test registration of sibboleth user upon new incoming request
        """
        

    def test_auth_sibbolleth(self):
        """ test whether the authentication mechanism sets the correct headers
        """


    def test_auth_headers(self):
        """ test whether the authentication mechanism sets the correct headers
        """
        #Check with non-existing user
        response = self.client.get( self.apibase + '/servers', {},
                                   **{'X-Auth-User':'notme',
                                      'X-Auth-Key':'0xdeadbabe'})
        self.assertEquals(response.status_code, 401)

        #Check with existing user
        response = self.client.get( self.apibase + '/', {},
                                   **{'X-Auth-User':'testuser',
                                      'X-Auth-Key':'testuserpasswd'})
        self.assertEquals(response.status_code, 204)
        self.assertNotEqual(response['X-Auth-Token'], None)
        self.assertEquals(response['X-Server-Management-Url'], '')
        self.assertEquals(response['X-Storage-Url'], '')
        self.assertEquals(response['X-CDN-Management-Url'], '')

        #Check access now that we do have an auth token
        token = response['X-Auth-Token']
        response = self.client.get (self.apibase + '/servers/detail', {},
                                   **{'X-Auth-Token': token})
        self.assertEquals(response.status_code, 200)
