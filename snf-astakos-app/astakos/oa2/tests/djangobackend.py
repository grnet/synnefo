# Copyright 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import urllib
import urlparse
import base64
import datetime

from collections import namedtuple

from django.test import TransactionTestCase as TestCase
from django.test import Client as TestClient

from django.core.urlresolvers import reverse
from django.utils import simplejson as json

from astakos.oa2.models import Client, AuthorizationCode, Token
from astakos.im.tests import common


ParsedURL = namedtuple('ParsedURL', ['host', 'scheme', 'path', 'params',
                                     'url'])


def parsed_url_wrapper(func):
    def wrapper(self, url, *args, **kwargs):
        url = self.parse_url(url)
        return func(self, url, *args, **kwargs)
    return wrapper


class URLAssertionsMixin(object):

    def get_redirect_url(self, request):
        return self.parse_url(request['Location'])

    def parse_url(self, url):
        if isinstance(url, ParsedURL):
            return url
        result = urlparse.urlparse(url)
        parsed = {
            'url': url,
            'host': result.netloc,
            'scheme': result.scheme,
            'path': result.path,
        }
        parsed['params'] = urlparse.parse_qs(result.query)
        return ParsedURL(**parsed)

    @parsed_url_wrapper
    def assertParamEqual(self, url, key, value):
        self.assertParam(url, key)
        self.assertEqual(url.params[key][0], value)

    @parsed_url_wrapper
    def assertNoParam(self, url, key):
        self.assertFalse(key in url.params,
                         "Url '%s' does contain '%s' parameter" % (url.url,
                                                                   key))

    @parsed_url_wrapper
    def assertParam(self, url, key):
        self.assertTrue(key in url.params,
                        "Url '%s' does not contain '%s' parameter" % (url.url,
                                                                      key))

    @parsed_url_wrapper
    def assertHost(self, url, host):
        self.assertEqual(url.host, host)

    @parsed_url_wrapper
    def assertPath(self, url, path):
        self.assertEqual(url.path, path)

    @parsed_url_wrapper
    def assertSecure(self, url, key):
        self.assertEqual(url.scheme, "https")


class OA2Client(TestClient):
    """
    An OAuth2 agnostic test client.
    """
    def __init__(self, baseurl, *args, **kwargs):
        self.oa2_url = baseurl
        self.token_url = self.oa2_url + 'token/'
        self.auth_url = self.oa2_url + 'auth/'
        self.credentials = kwargs.pop('credentials', ())

        kwargs['wsgi.url_scheme'] = 'https'
        return super(OA2Client, self).__init__(*args, **kwargs)

    def request(self, *args, **kwargs):
        #print kwargs.get('PATH_INFO') + '?' + kwargs.get('QUERY_STRING'), \
            #kwargs.get('HTTP_AUTHORIZATION', None)
        return super(OA2Client, self).request(*args, **kwargs)

    def get_url(self, token_or_auth, **params):
        return token_or_auth + '?' + urllib.urlencode(params)

    def grant(self, clientid, *args, **kwargs):
        """
        Do an authorization grant request.
        """
        params = {
            'grant_type': 'authorization_code',
            'client_id': clientid
        }
        urlparams = kwargs.pop('urlparams', {})
        params.update(urlparams)
        self.set_auth_headers(kwargs)
        return self.get(self.get_url(self.token_url, **params), *args,
                        **kwargs)

    def authorize_code(self, clientid, *args, **kwargs):
        """
        Do an authorization code request.
        """
        params = {
            'response_type': 'code',
            'client_id': clientid
        }
        urlparams = kwargs.pop('urlparams', {})
        urlparams.update(kwargs.pop('extraparams', {}))
        params.update(urlparams)
        self.set_auth_headers(kwargs)
        if 'reject' in params:
            return self.post(self.get_url(self.auth_url), data=params,
                             **kwargs)
        return self.get(self.get_url(self.auth_url, **params), *args, **kwargs)

    def access_token(self, code,
                     content_type='application/x-www-form-urlencoded',
                     **kwargs):
        """
        Do an get token request.
        """
        params = {
            'grant_type': 'authorization_code',
            'code': code
        }
        params.update(kwargs)
        self.set_auth_headers(kwargs)
        return self.post(self.token_url, data=urllib.urlencode(params),
                         content_type=content_type, **kwargs)

    def set_auth_headers(self, params):
        if not self.credentials:
            return
        credentials = base64.encodestring('%s:%s' % self.credentials).strip()
        params['HTTP_AUTHORIZATION'] = 'Basic %s' % credentials
        return params

    def set_credentials(self, user=None, pwd=None):
        self.credentials = (user, pwd)
        if not user and not pwd:
            self.credentials = ()


class TestOA2(TestCase, URLAssertionsMixin):

    def assertCount(self, model, count):
        self.assertEqual(model.objects.count(), count)

    def assert_access_token_response(self, r, expected):
        self.assertEqual(r.status_code, 200)
        try:
            data = json.loads(r.content)
        except:
            self.fail("Unexpected response content")

        self.assertTrue('access_token' in data)
        access_token = data['access_token']
        self.assertTrue('token_type' in data)
        token_type = data['token_type']
        self.assertTrue('expires_in' in data)
        expires_in = data['expires_in']

        try:
            token = Token.objects.get(code=access_token)
            self.assertEqual(token.expires_at,
                             token.created_at +
                             datetime.timedelta(seconds=expires_in))
            self.assertEqual(token.token_type, token_type)
            self.assertEqual(token.grant_type, 'authorization_code')
            #self.assertEqual(token.user, expected.get('user'))
            self.assertEqual(token.redirect_uri, expected.get('redirect_uri'))
            self.assertEqual(token.scope, expected.get('scope'))
            self.assertEqual(token.state, expected.get('state'))
        except Token.DoesNotExist:
            self.fail("Invalid access_token")

    def setUp(self):
        baseurl = reverse('oauth2_authenticate').replace('/auth', '/')
        self.client = OA2Client(baseurl)
        client1 = Client.objects.create(identifier="client1", secret="secret")
        self.client1_redirect_uri = "https://server.com/handle_code"
        client1.redirecturl_set.create(url=self.client1_redirect_uri)

        client2 = Client.objects.create(identifier="client2", type='public')
        self.client2_redirect_uri = "https://server2.com/handle_code"
        client2.redirecturl_set.create(url=self.client2_redirect_uri)

        client3 = Client.objects.create(identifier="client3", secret='secret',
                                        is_trusted=True)
        self.client3_redirect_uri = "https://server3.com/handle_code"
        client3.redirecturl_set.create(url=self.client3_redirect_uri)

        common.get_local_user("user@synnefo.org", password="password")

    def test_code_authorization(self):
        # missing response_type
        r = self.client.get(self.client.get_url(self.client.auth_url))
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # invalid response_type
        r = self.client.get(self.client.get_url(self.client.auth_url,
                                                response_type='invalid'))
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # unsupported response_type
        r = self.client.get(self.client.get_url(self.client.auth_url,
                                                response_type='token'))
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # missing client_id
        r = self.client.get(self.client.get_url(self.client.auth_url,
                                                response_type='code'))
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # fake client
        r = self.client.authorize_code('client-fake')
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # mixed up credentials/client_id's
        self.client.set_credentials('client1', 'secret')
        r = self.client.authorize_code('client2')
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # invalid credentials
        self.client.set_credentials('client2', '')
        r = self.client.authorize_code('client2')
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # invalid redirect_uri: not absolute URI
        self.client.set_credentials()
        params = {'redirect_uri':
                  urlparse.urlparse(self.client1_redirect_uri).path}
        r = self.client.authorize_code('client1', urlparams=params)
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # mismatching redirect uri
        self.client.set_credentials()
        params = {'redirect_uri': self.client1_redirect_uri[1:]}
        r = self.client.authorize_code('client1', urlparams=params)
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # valid request: untrusted client
        params = {'redirect_uri': self.client1_redirect_uri,
                  'scope': self.client1_redirect_uri,
                  'extra_param': '123'}
        self.client.set_credentials('client1', 'secret')
        r = self.client.authorize_code('client1', urlparams=params)
        self.assertEqual(r.status_code, 302)
        self.assertTrue('Location' in r)
        self.assertHost(r['Location'], "testserver:80")
        self.assertPath(r['Location'], reverse('login'))

        self.client.set_credentials('client1', 'secret')
        self.client.login(username="user@synnefo.org", password="password")
        r = self.client.authorize_code('client1', urlparams=params)
        self.assertEqual(r.status_code, 200)

        r = self.client.authorize_code('client1', urlparams=params,
                                       extraparams={'reject': 0})
        self.assertCount(AuthorizationCode, 1)

        # redirect is valid
        redirect1 = self.get_redirect_url(r)
        self.assertParam(redirect1, "code")
        self.assertNoParam(redirect1, "extra_param")
        self.assertHost(redirect1, "server.com")
        self.assertPath(redirect1, "/handle_code")

        params['state'] = 'csrfstate'
        params['scope'] = 'resource1'
        r = self.client.authorize_code('client1', urlparams=params)
        redirect2 = self.get_redirect_url(r)
        self.assertParamEqual(redirect2, "state", 'csrfstate')
        self.assertCount(AuthorizationCode, 2)

        code1 = AuthorizationCode.objects.get(code=redirect1.params['code'][0])
        #self.assertEqual(code1.state, '')
        self.assertEqual(code1.state, None)
        self.assertEqual(code1.redirect_uri, self.client1_redirect_uri)

        code2 = AuthorizationCode.objects.get(code=redirect2.params['code'][0])
        self.assertEqual(code2.state, 'csrfstate')
        self.assertEqual(code2.redirect_uri, self.client1_redirect_uri)

        # valid request: trusted client
        params = {'redirect_uri': self.client3_redirect_uri,
                  'scope': self.client3_redirect_uri,
                  'extra_param': '123'}
        self.client.set_credentials('client3', 'secret')
        r = self.client.authorize_code('client3', urlparams=params)
        self.assertEqual(r.status_code, 302)
        self.assertCount(AuthorizationCode, 3)

        # redirect is valid
        redirect3 = self.get_redirect_url(r)
        self.assertParam(redirect1, "code")
        self.assertNoParam(redirect3, "state")
        self.assertNoParam(redirect3, "extra_param")
        self.assertHost(redirect3, "server3.com")
        self.assertPath(redirect3, "/handle_code")

        code3 = AuthorizationCode.objects.get(code=redirect3.params['code'][0])
        self.assertEqual(code3.state, None)
        self.assertEqual(code3.redirect_uri, self.client3_redirect_uri)

        # valid request: trusted client
        params['state'] = 'csrfstate'
        self.client.set_credentials('client3', 'secret')
        r = self.client.authorize_code('client3', urlparams=params)
        self.assertEqual(r.status_code, 302)
        self.assertCount(AuthorizationCode, 4)

        # redirect is valid
        redirect4 = self.get_redirect_url(r)
        self.assertParam(redirect4, "code")
        self.assertParamEqual(redirect4, "state", 'csrfstate')
        self.assertNoParam(redirect4, "extra_param")
        self.assertHost(redirect4, "server3.com")
        self.assertPath(redirect4, "/handle_code")

        code4 = AuthorizationCode.objects.get(code=redirect4.params['code'][0])
        self.assertEqual(code4.state, 'csrfstate')
        self.assertEqual(code4.redirect_uri, self.client3_redirect_uri)

    def test_get_token(self):
        # invalid method
        r = self.client.get(self.client.token_url)
        self.assertEqual(r.status_code, 405)
        self.assertTrue('Allow' in r)
        self.assertEqual(r['Allow'], 'POST')

        # invalid content type
        r = self.client.post(self.client.token_url)
        self.assertEqual(r.status_code, 400)

        # missing grant type
        r = self.client.post(self.client.token_url,
                             content_type='application/x-www-form-urlencoded')
        self.assertEqual(r.status_code, 400)

        # unsupported grant type: client_credentials
        r = self.client.post(self.client.token_url,
                             data='grant_type=client_credentials',
                             content_type='application/x-www-form-urlencoded')
        self.assertEqual(r.status_code, 400)

        # unsupported grant type: token
        r = self.client.post(self.client.token_url,
                             data='grant_type=token',
                             content_type='application/x-www-form-urlencoded')
        self.assertEqual(r.status_code, 400)

        # invalid grant type
        r = self.client.post(self.client.token_url,
                             data='grant_type=invalid',
                             content_type='application/x-www-form-urlencoded')
        self.assertEqual(r.status_code, 400)

        # generate authorization code: without redirect_uri
        self.client.login(username="user@synnefo.org", password="password")
        r = self.client.authorize_code('client3')
        self.assertCount(AuthorizationCode, 1)
        redirect = self.get_redirect_url(r)
        code_instance = AuthorizationCode.objects.get(
            code=redirect.params['code'][0])

        # no client_id & no client authorization
        r = self.client.access_token(code_instance.code)
        self.assertEqual(r.status_code, 400)

        # invalid client_id
        r = self.client.access_token(code_instance.code, client_id='client2')
        self.assertEqual(r.status_code, 400)

        # inexistent client_id
        r = self.client.access_token(code_instance.code, client_id='client42')
        self.assertEqual(r.status_code, 400)

        # no client authorization
        r = self.client.access_token(code_instance.code, client_id='client3')
        self.assertEqual(r.status_code, 400)

        # mixed up credentials/client_id's
        self.client.set_credentials('client1', 'secret')
        r = self.client.access_token(code_instance.code, client_id='client3')
        self.assertEqual(r.status_code, 400)

        # mixed up credentials/client_id's
        self.client.set_credentials('client3', 'secret')
        r = self.client.access_token(code_instance.code, client_id='client1')
        self.assertEqual(r.status_code, 400)

        # mismatching client
        self.client.set_credentials('client1', 'secret')
        r = self.client.access_token(code_instance.code, client_id='client1')
        self.assertEqual(r.status_code, 400)

        # invalid code
        self.client.set_credentials('client3', 'secret')
        r = self.client.access_token('invalid')
        self.assertEqual(r.status_code, 400)

        # valid request
        self.client.set_credentials('client3', 'secret')
        r = self.client.access_token(code_instance.code)
        self.assertCount(AuthorizationCode, 0)  # assert code is consumed
        self.assertCount(Token, 1)
        expected = {'redirect_uri': self.client3_redirect_uri,
                    'scope': self.client3_redirect_uri,
                    'state': None}
        self.assert_access_token_response(r, expected)
