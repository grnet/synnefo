#
# Unit Tests for api
#
# Provides automated tests for api module
#
# Copyright 2011 Greek Research and Technology Network
#

from django.test import TestCase
from django.test.client import Client

from synnefo.logic.shibboleth import Tokens
from synnefo.db.models import SynnefoUser

class AuthTestCase(TestCase):
    fixtures = ['api_test_data']
    apibase = '/api/v1.1'

    def setUp(self):
        self.client = Client()

    def test_auth_shibboleth(self):
        """ test redirect to shibboleth page
        """
        response = self.client.get(self.apibase + '/servers')
        self.assertEquals(response.status_code, 302)

    def test_register_shibboleth_user(self):
        """ test registration of sibboleth user upon new incoming request
        """
        response = self.client.get(self.apibase + '/servers', {},
                                   **{Tokens.SIB_GIVEN_NAME: 'Jimmy',
                                      Tokens.SIB_EDU_PERSON_PRINCIPAL_NAME: 'jh@gmail.com',
                                      Tokens.SIB_DISPLAY_NAME: 'Jimmy Hendrix'})

        user = None
        try:
            user = SynnefoUser.objects.get(uniq = "jh@gmail.com")
        except SynnefoUser.DoesNotExist:
            self.assertNotEqual(user, None)
        self.assertNotEqual(user, None)

    def test_auth_headers(self):
        """ test whether the authentication mechanism sets the correct headers
        """
        #Check with non-existing user
        response = self.client.get(self.apibase + '/servers', {},
                                   **{'X-Auth-User': 'notme',
                                      'X-Auth-Key': '0xdeadbabe'})
        self.assertEquals(response.status_code, 401)

        #Check with existing user
        response = self.client.get(self.apibase + '/', {},
                                   **{'X-Auth-User': 'testuser',
                                      'X-Auth-Key': 'testuserpasswd'})
        self.assertEquals(response.status_code, 204)
        self.assertNotEqual(response['X-Auth-Token'], None)
        self.assertEquals(response['X-Server-Management-Url'], '')
        self.assertEquals(response['X-Storage-Url'], '')
        self.assertEquals(response['X-CDN-Management-Url'], '')

        #Check access now that we do have an auth token
        token = response['X-Auth-Token']
        response = self.client.get(self.apibase + '/servers/detail', {},
                                   **{'X-Auth-Token': token})
        self.assertEquals(response.status_code, 200)
