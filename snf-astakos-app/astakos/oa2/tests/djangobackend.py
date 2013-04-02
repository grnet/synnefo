import urllib
import urlparse
import base64

from collections import namedtuple

from django.test import TransactionTestCase as TestCase
from django.test import Client as TestClient

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from astakos.oa2.models import Client, RedirectUrl, AuthorizationCode


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
            self.post(self.get_url(self.auth_url), data=params)
        return self.get(self.get_url(self.auth_url, **params), *args, **kwargs)

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

    def setUp(self):
        baseurl = reverse('oa2_authenticate').replace('/auth', '/')
        self.client = OA2Client(baseurl)
        client1 = Client.objects.create(identifier="client1", secret="secret")
        client2 = Client.objects.create(identifier="client2", type='public')
        self.client2_redirect_uri = "https://server2.com/handle_code"
        client2.redirecturl_set.create(url=self.client2_redirect_uri)
        self.client1_redirect_uri = "https://server.com/handle_code"
        client1.redirecturl_set.create(url=self.client1_redirect_uri)

        u = User.objects.create(username="user@synnefo.org")
        u.set_password("password")
        u.save()

    def test_code_authorization(self):
        r = self.client.authorize_code('client-fake')
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # no auth header, client is confidential
        r = self.client.authorize_code('client1')
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # no redirect_uri
        #self.client.credentials = ('client1', 'secret')
        #r = self.client.authorize_code('client1')
        #self.assertEqual(r.status_code, 400)
        #self.assertCount(AuthorizationCode, 0)

        # mixed up credentials/client_id's
        self.client.set_credentials('client1', 'secret')
        r = self.client.authorize_code('client2')
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        self.client.set_credentials('client2', '')
        r = self.client.authorize_code('client2')
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        self.client.set_credentials()
        r = self.client.authorize_code('client1')
        self.assertEqual(r.status_code, 400)
        self.assertCount(AuthorizationCode, 0)

        # valid request
        params = {'redirect_uri': self.client1_redirect_uri,
                  'extra_param': '123'}
        self.client.set_credentials('client1', 'secret')
        r = self.client.authorize_code('client1', urlparams=params)
        self.assertEqual(r.status_code, 302)

        self.client.set_credentials()
        self.client.login(username="user@synnefo.org", password="password")
        r = self.client.authorize_code('client1', urlparams=params)
        print r
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
        self.assertEqual(code1.state, '')
        self.assertEqual(code1.redirect_uri, self.client1_redirect_uri)

        code2 = AuthorizationCode.objects.get(code=redirect2.params['code'][0])
        self.assertEqual(code2.state, 'csrfstate')
        self.assertEqual(code2.redirect_uri, self.client1_redirect_uri)
