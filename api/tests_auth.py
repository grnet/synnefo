#
# Unit Tests for api
#
# Provides automated tests for api module
#
# Copyright 2011 Greek Research and Technology Network
#

from django.test import TestCase
from django.test.client import Client
from django.conf import settings

from synnefo.logic.shibboleth import Tokens, NoUniqueToken
from synnefo.db.models import SynnefoUser

from datetime import datetime, timedelta

class AuthTestCase(TestCase):
    fixtures = ['api_test_data', 'auth_test_data']
    apibase = '/api/v1.1'

    def setUp(self):
        self.client = Client()

    def test_shibboleth_correct_request(self):
        """test request that should succeed and register a user
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
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'], "http://testserver/")
        self.assertTrue('X-Auth-Token' in response)
        self.assertEquals(response['X-Auth-Token'], user.auth_token)

    def test_shibboleth_no_uniq_request(self):
        """test a request with no unique field
        """
        response = self.client.get(self.apibase + '/servers', {},
                                    **{Tokens.SIB_GIVEN_NAME: 'Jimmy',
                                    Tokens.SIB_DISPLAY_NAME: 'Jimmy Hendrix'})
        self._test_redirect(response)

    def test_shibboleth_wrong_from_request(self):
        """ test request from wrong host
        """
        response = self.client.get(self.apibase + '/servers', {},
                                   **{Tokens.SIB_GIVEN_NAME: 'Jimmy',
                                      Tokens.SIB_EDU_PERSON_PRINCIPAL_NAME: 'jh@gmail.com',
                                      Tokens.SIB_DISPLAY_NAME: 'Jimmy Hendrix',
                                      'REMOTE_ADDR': '1.2.3.4',
                                      'SERVER_NAME': 'nohost.nodomain'})
        self._test_redirect(response)

    def test_shibboleth_expired_token(self):
        """ test request from expired token
        """
        user = SynnefoUser.objects.get(uniq = "test@synnefo.gr")
        self.assertNotEqual(user.auth_token_created, None)
        user.auth_token_created = (datetime.now() -
                                   timedelta(hours = settings.AUTH_TOKEN_DURATION))
        user.save()
        response = self.client.get(self.apibase + '/servers', {},
                                   **{'X-Auth-Token': user.auth_token})
        self._test_redirect(response)

    def test_shibboleth_redirect(self):
        """ test redirect to Sibboleth page
        """
        response = self.client.get(self.apibase + '/servers')
        self._test_redirect(response)

    def test_shibboleth_auth(self):
        """ test authentication with X-Auth-Token
        """
        user = SynnefoUser.objects.get(uniq = "test@synnefo.gr")
        response = self.client.get(self.apibase + '/servers', {},
                                   **{'X-Auth-Token': user.auth_token})
        self.assertTrue(response.status_code, 200)
        self.assertTrue('Vary' in response)
        self.assertTrue('X-Auth-Token' in response['Vary'])

    def test_fail_oapi_auth(self):
        """ test authentication from not registered user using OpenAPI
        """
        response = self.client.get(self.apibase + '/servers', {},
                                   **{'X-Auth-User': 'notme',
                                      'X-Auth-Key': '0xdeadbabe'})
        self.assertEquals(response.status_code, 401)

    def test_oapi_auth(self):
        """authentication with user registration
        """
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

    def _test_redirect(self, response):
        self.assertEquals(response.status_code, 302)
        self.assertTrue('Location' in response)
        self.assertEquals(response['Location'], settings.SHIBBOLETH_HOST)