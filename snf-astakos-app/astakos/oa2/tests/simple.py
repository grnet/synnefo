# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import base64
import urllib

from astakos.oa2.backends import SimpleBackend
from astakos.oa2.backends.base import Token, Client, AuthorizationCode, User
from astakos.oa2.backends.base import Request, Response, OA2Error


# Test helpers
class OA2TestCase(unittest.TestCase):

    def _get_request(self, method, get, post, meta, secure):
        return Request(method=method, GET=get, POST=post, META=meta,
                       secure=secure)

    def auth_request(self, request, username, secret):
        username = urllib.quote_plus(username)
        secret = urllib.quote_plus(secret)
        b64 = base64.encodestring('%s:%s' % (username, secret))[:-1]
        request.META['Authorization'] = 'Basic %s' % b64

    def build_authorization_request(self, type, client_id, scope=None,
                                    state=None, uri=None, **extra):
        method = extra.get('method', 'GET')
        if method == 'POST':
            extra_params = extra.get('post', {})
            params = {}
            post = params
            get = extra.get('get', {})
        else:
            extra_params = extra.get('get', {})
            params = {}
            get = params
            post = extra.get('post', {})

        params.update({'response_type': type, 'client_id': client_id})
        if not state is None:
            params['state'] = state
        if not scope is None:
            params['scope'] = scope
        if not uri is None:
            params['redirect_uri'] = uri

        params.update(extra_params)

        secure = extra.get('secure', True)
        meta = extra.get('meta', None)
        return self._get_request(method, get, post, meta, secure)

    def build_token_request(self, grant_type, client_id, scope=None,
                            state=None, uri=None, **extra):
        method = extra.get('method', 'POST')
        params = {'grant_type': grant_type, 'client_id': client_id}
        if method == 'POST':
            extra_params = extra.get('post', {})
            post = params
            get = extra.get('get', {})
        else:
            extra_params = extra.get('get', {})
            get = params
            post = extra.get('post', {})

        if scope:
            params['scope'] = scope
        if state:
            params['state'] = state
        if uri:
            params['redirect_uri'] = uri

        params.update(extra_params)

        secure = extra.get('secure', True)
        meta = extra.get('meta', None)
        return self._get_request(method, get, post, meta, secure)

    def assertRaisesOA2(self, *args, **kwargs):
        return self.assertRaises(OA2Error, *args, **kwargs)

    def assertResponseRedirect(self, response, url=None):
        self.assertResponseStatus(response, status=302)
        self.assertResponseContains(response, 'Location')
        if not url is None:
            self.assertEqual(response.headers.get('Location'), url)

    def assertResponseStatus(self, response, status=200):
        self.assertEqual(response.status, status)

    def assertResponseContains(self, response, header, value=None):
        if not header in response.headers:
            raise AssertionError("Response does not contain '%s'" % header)
        if value is None:
            return
        self.assertEqual(response.headers.get(header), value)


class TestClient(OA2TestCase):

    def _cleanup(self):
        Client.ENTRIES = {}
        Token.ENTRIES = {}
        User.ENTRIES = {}
        AuthorizationCode.ENTRIES = {}

    def setUp(self):
        self._cleanup()
        uris = ['http://client1.synnefo.org/oauth2_callback']
        self.client_public = Client.create('client_public', uris=uris,
                                           client_type='public')
        self.client_conf = Client.create('client_conf', secret='pass',
                                         uris=uris, client_type='confidential')
        self.backend = SimpleBackend(errors_to_http=False)

    def test_authorization(self):
        client_id = self.client_public.get_id()
        auth_request = self.build_authorization_request
        token_request = self.build_token_request
        User.create("kpap@grnet.gr", name='kpap')

        def assert_codes_len(check=0):
            self.assertEqual(len(AuthorizationCode.ENTRIES.keys()), check)

        # plain http code request
        req = auth_request('code', client_id, secure=False)
        self.assertRaisesOA2(self.backend.authorize, req)
        assert_codes_len(0)

        # wrong method
        req = auth_request('code', client_id, method='POST')
        self.assertRaisesOA2(self.backend.authorize, req)
        assert_codes_len(0)

        # invalid client id
        req = auth_request('code', 'client123')
        self.assertRaisesOA2(self.backend.authorize, req)
        assert_codes_len(0)

        # invalid redirect uri
        invalid_uri = 'http://client1.synnefo.org/oauth2_callback?invalid'
        req = auth_request('code', client_id, uri=invalid_uri)
        self.assertRaisesOA2(self.backend.authorize, req)
        assert_codes_len(0)

        # code request
        req = auth_request('code', client_id, scope="scope1 scope2")
        res = self.backend.authorize(req)
        self.assertResponseRedirect(res)
        assert_codes_len(1)

        # authorize grant
        auth_code = AuthorizationCode.ENTRIES.keys()[0]
        req = token_request('authorization_code', client_id,
                            scope="scope1 scope2", post={'code': auth_code})

        # invalid code
        req.POST['code'] = "123"
        self.assertRaisesOA2(self.backend.grant, req)

        # valid code
        req.POST['code'] = auth_code
        res = self.backend.grant(req)

        # code consumed
        assert_codes_len(0)

        # code reuse fails
        self.assertRaisesOA2(self.backend.grant, req)

        # valid token scope
        token = Token.ENTRIES.keys()[0]
        token_obj = Token.get(token)
        self.assertEqual(token_obj.scope, "scope1 scope2")

    def test_authenticated_client(self):
        client_id = self.client_conf.get_id()
        client_secret = self.client_conf.secret
        auth_request = self.build_authorization_request
        token_request = self.build_token_request

        req = auth_request('code', client_id, scope="scope1 scope2")
        self.auth_request(req, client_id, client_secret)

    def test_invalid_client(self):
        client_id = self.client_public.get_id()
        auth_request = self.build_authorization_request
        token_request = self.build_token_request

        # code request
        req = auth_request('code', 'client5', scope="scope1 scope2")
        self.assertRaisesOA2(self.backend.authorize, req)

        req = auth_request('code', client_id, scope="scope1 scope2")
        self.backend.authorize(req)

        auth_code = AuthorizationCode.ENTRIES.keys()[0]
        req = token_request('authorization_code', 'fakeclient',
                            scope="scope1 scope2", post={'code': auth_code})
        self.assertRaisesOA2(self.backend.grant, req)

        req.POST['client_id'] = client_id
        self.backend.grant(req)


if __name__ == '__main__':
    unittest.main()
