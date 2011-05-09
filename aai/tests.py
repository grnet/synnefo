#
# Unit Tests for aai
#
# Provides automated tests for aai module. The tests
#
# Copyright 2011 Greek Research and Technology Network
#
from Cookie import Cookie

from django.test import TestCase
from django.test.client import Client
from django.conf import settings

from synnefo.db.models import SynnefoUser

from datetime import datetime, timedelta

from synnefo.aai.shibboleth import Tokens, NoUniqueToken

class AaiTestCase(TestCase):
    fixtures = ['api_test_data', 'auth_test_data']
    apibase = '/api/v1.1'

    def setUp(self):
        self.client = Client()

    def test_shibboleth_correct_request(self):
        """test request that should succeed and register a user
        """
        response = self.client.get('/index.html', {},
                                   **{Tokens.SIB_NAME: 'Jimmy',
                                      Tokens.SIB_EPPN: 'jh@gmail.com',
                                      Tokens.SIB_CN: 'Jimmy Hendrix',
                                      Tokens.SIB_SESSION_ID: '123321',
                                      'TEST-AAI' : 'true'})
        user = None
        try:
            user = SynnefoUser.objects.get(uniq = "jh@gmail.com")
        except SynnefoUser.DoesNotExist:
            self.assertNotEqual(user, None)
        self.assertNotEqual(user, None)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'], settings.APP_INSTALL_URL)
        self.assertTrue('X-Auth-Token' in response)
        self.assertEquals(response['X-Auth-Token'], user.auth_token)
        #self.assertNotEquals(response.cookies['X-Auth-Token'].find(user.auth_token), -1)


    def test_shibboleth_no_uniq_request(self):
        """test a request with no unique field
        """
        response = self.client.get('/index.html', {},
                               **{Tokens.SIB_NAME: 'Jimmy',
                                  Tokens.SIB_CN: 'Jimmy Hendrix',
                                  'TEST-AAI': 'true'})
        self._test_redirect(response)


    def test_shibboleth_expired_token(self):
        """ test request from expired token
        """
        user = SynnefoUser.objects.get(uniq="test@synnefo.gr")
        self.assertNotEqual(user.auth_token_created, None)
        self._update_user_ts(user)
        response = self.client.get('/index.html', {},
                               **{'X-Auth-Token': user.auth_token,
                                  'TEST-AAI': 'true'})
        self._test_redirect(response)

    def test_shibboleth_redirect(self):
        """ test redirect to Sibboleth page
        """
        response = self.client.get('/index.html', {}, **{'TEST-AAI': 'true'})
        self._test_redirect(response)

    def test_shibboleth_auth(self):
        """ test authentication with X-Auth-Token
        """
        user = SynnefoUser.objects.get(uniq="test@synnefo.gr")
        response = self.client.get('/index.html', {},
                               **{'X-Auth-Token': user.auth_token,
                                  'TEST-AAI': 'true'})
        self.assertTrue(response.status_code, 200)
        self.assertTrue('Vary' in response)
        self.assertTrue('X-Auth-Token' in response['Vary'])

    def _test_redirect(self, response):
        self.assertEquals(response.status_code, 302)
        self.assertTrue('Location' in response)
        self.assertTrue(response['Location'].endswith(settings.LOGIN_PATH))

    def _update_user_ts(self, user):
        user.auth_token_created = (datetime.now() -
                                   timedelta(hours = settings.AUTH_TOKEN_DURATION))
        user.save()