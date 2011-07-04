# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

# Provides automated tests for aai module. The tests

from django.test import TestCase
from django.test.client import Client
from django.conf import settings

from synnefo.db.models import SynnefoUser

from datetime import datetime, timedelta

from synnefo.aai.shibboleth import Tokens


class AaiTestCase(TestCase):
    fixtures = ['api_test_data', 'auth_test_data']
    apibase = '/api/v1.1'

    def setUp(self):
        self.client = Client()

    def test_shibboleth_correct_request(self):
        """test request that should succeed and register a user
        """
        response = self.client.get('/index.html', {},
                                   **{Tokens.SHIB_NAME: 'Jimmy',
                                      Tokens.SHIB_EPPN: 'jh@gmail.com',
                                      Tokens.SHIB_CN: 'Jimmy Hendrix',
                                      Tokens.SHIB_SESSION_ID: '123321',
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
                               **{Tokens.SHIB_NAME: 'Jimmy',
                                  Tokens.SHIB_CN: 'Jimmy Hendrix',
                                  'TEST-AAI': 'true'})
        self._test_redirect(response)

    def test_shibboleth_expired_token(self):
        """ test request from expired token
        """
        user = SynnefoUser.objects.get(uniq="test@synnefo.gr")
        self.assertNotEqual(user.auth_token_expires, None)
        user.auth_token_expires = datetime.now()
        user.save()
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

    def test_auth_cookie(self):
        user = SynnefoUser.objects.get(uniq = "test@synnefo.gr")
        self.client.cookies['X-Auth-Token'] = user.auth_token
        response = self.client.get('/', {},
                                   **{'X-Auth-Token': user.auth_token,
                                      'TEST-AAI' : 'true'})
        self.assertTrue(response.status_code, 200)
        self.assertTrue('Vary' in response)
        self.assertTrue('X-Auth-Token' in response['Vary'])

    def _test_redirect(self, response):
        self.assertEquals(response.status_code, 302)
        self.assertTrue('Location' in response)
        self.assertTrue(response['Location'].startswith(settings.LOGIN_URL))

