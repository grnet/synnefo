#!/usr/bin/env python
#
# Copyright (C) 2012, 2013 GRNET S.A. All rights reserved.
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

"""Unit Tests for the astakos-client module

Provides unit tests for the code implementing
the astakos client library

"""

import re
import sys
import socket
import simplejson
from mock import patch
from contextlib import contextmanager

import astakosclient
from astakosclient import AstakosClient
from astakosclient.utils import join_urls
from astakosclient.errors import \
    AstakosClientException, Unauthorized, BadRequest, NotFound, \
    NoUserName, NoUUID, BadValue, QuotaLimit

# Use backported unittest functionality if Python < 2.7
try:
    import unittest2 as unittest
except ImportError:
    if sys.version_info < (2, 7):
        raise Exception("The unittest2 package is required for Python < 2.7")
    import unittest


# --------------------------------------------------------------------
# Helper functions
auth_url = "https://example.org/identity/v2.0"
account_prefix = "/account_prefix"
ui_prefix = "/ui_prefix"
api_authenticate = join_urls(account_prefix, "authenticate")
api_usercatalogs = join_urls(account_prefix, "user_catalogs")
api_resources = join_urls(account_prefix, "resources")
api_quotas = join_urls(account_prefix, "quotas")
api_commissions = join_urls(account_prefix, "commissions")

# --------------------------------------
# Local users
token_1 = "skzleaFlBl+fasFdaf24sx"
user_1 = \
    {"username": "user1@example.com",
     "name": "Example User One",
     "email": ["user1@example.com"],
     "uuid": "73917abc-abcd-477e-a1f1-1763abcdefab"}

resources = {
    "cyclades.ram": {
        "unit": "bytes",
        "description": "Virtual machine memory",
        "service": "cyclades"}}

endpoints = {
    "access": {
        "serviceCatalog": [{
            "endpoints": [{"SNF:uiURL": join_urls("https://example.org/",
                                                  ui_prefix),
                           "publicURL": join_urls("https://example.org/",
                                                  account_prefix),
                           "region": "default",
                           "versionId": "v1.0"}],
            "name": "astakos_account",
            "type": "account"}]
        }
    }

quotas = {
    "system": {
        "cyclades.ram": {
            "pending": 0,
            "limit": 1073741824,
            "usage": 536870912},
        "cyclades.vm": {
            "pending": 0,
            "limit": 2,
            "usage": 2}},
    "project:1": {
        "cyclades.ram": {
            "pending": 0,
            "limit": 2147483648,
            "usage": 2147483648},
        "cyclades.vm": {
            "pending": 1,
            "limit": 5,
            "usage": 2}}}

commission_request = {
    "force": False,
    "auto_accept": False,
    "name": "my commission",
    "provisions": [
        {
            "holder": "c02f315b-7d84-45bc-a383-552a3f97d2ad",
            "source": "system",
            "resource": "cyclades.vm",
            "quantity": 1
        },
        {
            "holder": "c02f315b-7d84-45bc-a383-552a3f97d2ad",
            "source": "system",
            "resource": "cyclades.ram",
            "quantity": 30000
        }]}

commission_successful_response = {"serial": 57}

commission_failure_response = {
    "overLimit": {
        "message": "a human-readable error message",
        "code": 413,
        "data": {
            "provision": {
                "holder": "c02f315b-7d84-45bc-a383-552a3f97d2ad",
                "source": "system",
                "resource": "cyclades.ram",
                "quantity": 520000000},
            "name": "NoCapacityError",
            "limit": 600000000,
            "usage": 180000000}}}

pending_commissions = [100, 200]

commission_description = {
    "serial": 57,
    "issue_time": "2013-04-08T10:19:15.0373+00:00",
    "name": "a commission",
    "provisions": [
        {
            "holder": "c02f315b-7d84-45bc-a383-552a3f97d2ad",
            "source": "system",
            "resource": "cyclades.vm",
            "quantity": 1
        },
        {
            "holder": "c02f315b-7d84-45bc-a383-552a3f97d2ad",
            "source": "system",
            "resource": "cyclades.ram",
            "quantity": 536870912
        }]}

resolve_commissions_req = {
    "accept": [56, 57],
    "reject": [56, 58, 59]}

resolve_commissions_rep = {
    "accepted": [57],
    "rejected": [59],
    "failed": [
        [56, {
            "badRequest": {
                "message": "cannot both accept and reject serial 56",
                "code": 400}}],
        [58, {
            "itemNotFound": {
                "message": "serial 58 does not exist",
                "code": 404}}]]}


# ----------------------------
# These functions will be used as mocked requests
def _request_offline(conn, method, url, **kwargs):
    """This request behaves as we were offline"""
    raise socket.gaierror


def _request_status_302(conn, method, url, **kwargs):
    """This request returns 302"""
    message = "FOUND"
    status = 302
    data = "302 Found"
    return (message, data, status)


def _request_status_404(conn, method, url, **kwargs):
    """This request returns 404"""
    message = "Not Found"
    status = 404
    data = "404 Not Found"
    return (message, data, status)


def _request_status_403(conn, method, url, **kwargs):
    """This request returns 403"""
    message = "UNAUTHORIZED"
    status = 403
    data = "Forbidden"
    return (message, data, status)


def _request_status_401(conn, method, url, **kwargs):
    """This request returns 401"""
    message = "UNAUTHORIZED"
    status = 401
    data = "Invalid X-Auth-Token\n"
    return (message, data, status)


def _request_status_400(conn, method, url, **kwargs):
    """This request returns 400"""
    message = "BAD REQUEST"
    status = 400
    data = "Method not allowed.\n"
    return (message, data, status)


def _request_ok(conn, method, url, **kwargs):
    """This request behaves like original Astakos does"""
    if api_authenticate == url:
        return _req_authenticate(conn, method, url, **kwargs)
    elif api_usercatalogs == url:
        return _req_catalogs(conn, method, url, **kwargs)
    elif api_resources == url:
        return _req_resources(conn, method, url, **kwargs)
    elif api_quotas == url:
        return _req_quotas(conn, method, url, **kwargs)
    elif url.startswith(api_commissions):
        return _req_commission(conn, method, url, **kwargs)
    else:
        return _request_status_404(conn, method, url, **kwargs)


def _req_authenticate(conn, method, url, **kwargs):
    """Check if user exists and return his profile"""
    global user_1, token_1

    # Check input
    if conn.__class__.__name__ != "HTTPSConnection":
        return _request_status_302(conn, method, url, **kwargs)
    if method != "GET":
        return _request_status_400(conn, method, url, **kwargs)
    token = kwargs['headers'].get('X-Auth-Token')
    if token == token_1:
        user = dict(user_1)
        return ("", simplejson.dumps(user), 200)
    else:
        # No user found
        return _request_status_401(conn, method, url, **kwargs)


def _req_catalogs(conn, method, url, **kwargs):
    """Return user catalogs"""
    global token_1, token_2, user_1, user_2

    # Check input
    if conn.__class__.__name__ != "HTTPSConnection":
        return _request_status_302(conn, method, url, **kwargs)
    if method != "POST":
        return _request_status_400(conn, method, url, **kwargs)
    token = kwargs['headers'].get('X-Auth-Token')
    if token != token_1:
        return _request_status_401(conn, method, url, **kwargs)

    # Return
    body = simplejson.loads(kwargs['body'])
    if 'uuids' in body:
        # Return uuid_catalog
        uuids = body['uuids']
        catalogs = {}
        if user_1['uuid'] in uuids:
            catalogs[user_1['uuid']] = user_1['username']
        return_catalog = {"displayname_catalog": {}, "uuid_catalog": catalogs}
    elif 'displaynames' in body:
        # Return displayname_catalog
        names = body['displaynames']
        catalogs = {}
        if user_1['username'] in names:
            catalogs[user_1['username']] = user_1['uuid']
        return_catalog = {"displayname_catalog": catalogs, "uuid_catalog": {}}
    else:
        return_catalog = {"displayname_catalog": {}, "uuid_catalog": {}}
    return ("", simplejson.dumps(return_catalog), 200)


def _req_resources(conn, method, url, **kwargs):
    """Return quota resources"""
    global resources

    # Check input
    if conn.__class__.__name__ != "HTTPSConnection":
        return _request_status_302(conn, method, url, **kwargs)
    if method != "GET":
        return _request_status_400(conn, method, url, **kwargs)

    # Return
    return ("", simplejson.dumps(resources), 200)


def _req_quotas(conn, method, url, **kwargs):
    """Return quotas for user_1"""
    global token_1, quotas

    # Check input
    if conn.__class__.__name__ != "HTTPSConnection":
        return _request_status_302(conn, method, url, **kwargs)
    if method != "GET":
        return _request_status_400(conn, method, url, **kwargs)
    token = kwargs['headers'].get('X-Auth-Token')
    if token != token_1:
        return _request_status_401(conn, method, url, **kwargs)

    # Return
    return ("", simplejson.dumps(quotas), 200)


def _req_commission(conn, method, url, **kwargs):
    """Perform a commission for user_1"""
    global token_1, pending_commissions, \
        commission_successful_response, commission_failure_response

    # Check input
    if conn.__class__.__name__ != "HTTPSConnection":
        return _request_status_302(conn, method, url, **kwargs)
    token = kwargs['headers'].get('X-Auth-Token')
    if token != token_1:
        return _request_status_401(conn, method, url, **kwargs)

    if method == "POST":
        if 'body' not in kwargs:
            return _request_status_400(conn, method, url, **kwargs)
        body = simplejson.loads(unicode(kwargs['body']))
        if re.match('/?'+api_commissions+'$', url) is not None:
            # Issue Commission
            # Check if we have enough resources to give
            if body['provisions'][1]['quantity'] > 420000000:
                return ("", simplejson.dumps(commission_failure_response), 413)
            else:
                return \
                    ("", simplejson.dumps(commission_successful_response), 200)
        else:
            # Issue commission action
            serial = url.split('/')[3]
            if serial == "action":
                # Resolve multiple actions
                if body == resolve_commissions_req:
                    return ("", simplejson.dumps(resolve_commissions_rep), 200)
                else:
                    return _request_status_400(conn, method, url, **kwargs)
            else:
                # Issue action for one commission
                if serial != str(57):
                    return _request_status_404(conn, method, url, **kwargs)
                if len(body) != 1:
                    return _request_status_400(conn, method, url, **kwargs)
                if "accept" not in body.keys() and "reject" not in body.keys():
                    return _request_status_400(conn, method, url, **kwargs)
                return ("", "", 200)

    elif method == "GET":
        if re.match('/?'+api_commissions+'$', url) is not None:
            # Return pending commission
            return ("", simplejson.dumps(pending_commissions), 200)
        else:
            # Return commissions's description
            serial = re.sub('/?' + api_commissions, '', url)[1:]
            if serial == str(57):
                return ("", simplejson.dumps(commission_description), 200)
            else:
                return _request_status_404(conn, method, url, **kwargs)
    else:
        return _request_status_400(conn, method, url, **kwargs)


# ----------------------------
# Mock the actual _doRequest
def _mock_request(new_requests):
    """Mock the actual request

    Given a list of requests to use (in rotation),
    replace the original _doRequest function with
    a new one

    """
    def _mock(conn, method, url, **kwargs):
        # Get first request
        request = _mock.requests[0]
        # Rotate requests
        _mock.requests = _mock.requests[1:] + _mock.requests[:1]
        # Use first request
        return request(conn, method, url, **kwargs)

    _mock.requests = new_requests
    # Replace `_doRequest' with our `_mock'
    astakosclient._do_request = _mock


# --------------------------------------
# Mock the get_endpoints method
@contextmanager
def patch_astakosclient(new_requests):
    _mock_request(new_requests)
    with patch('astakosclient.AstakosClient.get_endpoints') as patcher:
        patcher.return_value = endpoints
        yield


# --------------------------------------------------------------------
# The actual tests

class TestCallAstakos(unittest.TestCase):
    """Test cases for function _callAstakos"""

    # ----------------------------------
    # Test the response we get if we don't have internet access
    def _offline(self, pool):
        global token_1, auth_url
        _mock_request([_request_offline])
        try:
            client = AstakosClient(token_1, auth_url, use_pool=pool)
            client._call_astakos("offline")
        except AstakosClientException:
            pass
        else:
            self.fail("Should have raised AstakosClientException")

    def test_offline(self):
        """Test _offline without pool"""
        self._offline(False)

    def test_offline_pool(self):
        """Test _offline using pool"""
        self._offline(True)

    # ----------------------------------
    # Test the response we get if we send invalid token
    def _invalid_token(self, pool):
        global auth_url
        token = "skaksaFlBl+fasFdaf24sx"
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token, auth_url, use_pool=pool)
                client.get_user_info()
        except Unauthorized:
            pass
        except Exception:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")
        else:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")

    def test_invalid_token(self):
        """Test _invalid_token without pool"""
        self._invalid_token(False)

    def test_invalid_token_pool(self):
        """Test _invalid_token using pool"""
        self._invalid_token(True)

    # ----------------------------------
    # Test the response we get if we send invalid url
    def _invalid_url(self, pool):
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url, use_pool=pool)
                client._call_astakos("/astakos/api/misspelled")
        except NotFound:
            pass
        except Exception, e:
            self.fail("Got \"%s\" instead of 404" % e)
        else:
            self.fail("Should have returned 404 (Not Found)")

    def test_invalid_url(self):
        """Test _invalid_url without pool"""
        self._invalid_url(False)

    def test_invalid_url_pool(self):
        """Test _invalid_url using pool"""
        self._invalid_url(True)

    # ----------------------------------
    # Test the response we get if we use an unsupported scheme
    def _unsupported_scheme(self, pool):
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, "ftp://example.com",
                                       use_pool=pool)
                client.get_user_info()
        except BadValue:
            pass
        except Exception:
            self.fail("Should have raise BadValue Exception")
        else:
            self.fail("Should have raise BadValue Exception")

    def test_unsupported_scheme(self):
        """Test _unsupported_scheme without pool"""
        self._unsupported_scheme(False)

    def test_unsupported_scheme_pool(self):
        """Test _unsupported_scheme using pool"""
        self._unsupported_scheme(True)

    # ----------------------------------
    # Test the response we get if we use http instead of https
    def _http_scheme(self, pool):
        global token_1
        http_auth_url = "http://example.org/identity/v2.0"
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, http_auth_url, use_pool=pool)
                client.get_user_info()
        except AstakosClientException as err:
            if err.status != 302:
                self.fail("Should have returned 302 (Found)")
        else:
            self.fail("Should have returned 302 (Found)")

    def test_http_scheme(self):
        """Test _http_scheme without pool"""
        self._http_scheme(False)

    def test_http_scheme_pool(self):
        """Test _http_scheme using pool"""
        self._http_scheme(True)

    # ----------------------------------
    # Test the response we get if we use authenticate with POST
    def _post_authenticate(self, pool):
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url, use_pool=pool)
                client._call_astakos(api_authenticate, method="POST")
        except BadRequest:
            pass
        except Exception:
            self.fail("Should have returned 400 (Method not allowed)")
        else:
            self.fail("Should have returned 400 (Method not allowed)")

    def test_post_authenticate(self):
        """Test _post_authenticate without pool"""
        self._post_authenticate(False)

    def test_post_authenticate_pool(self):
        """Test _post_authenticate using pool"""
        self._post_authenticate(True)

    # ----------------------------------
    # Test the response if we request user_catalogs with GET
    def _get_user_catalogs(self, pool):
        global token_1, auth_url, api_usercatalogs
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url, use_pool=pool)
                client._call_astakos(api_usercatalogs)
        except BadRequest:
            pass
        except Exception:
            self.fail("Should have returned 400 (Method not allowed)")
        else:
            self.fail("Should have returned 400 (Method not allowed)")

    def test_get_user_catalogs(self):
        """Test _get_user_catalogs without pool"""
        self._get_user_catalogs(False)

    def test_get_user_catalogs_pool(self):
        """Test _get_user_catalogs using pool"""
        self._get_user_catalogs(True)


class TestAuthenticate(unittest.TestCase):
    """Test cases for function getUserInfo"""

    # ----------------------------------
    # Test the response we get if we don't have internet access
    def test_offline(self):
        """Test offline after 3 retries"""
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_offline]):
                client = AstakosClient(token_1, auth_url, retry=3)
                client.get_user_info()
        except AstakosClientException:
            pass
        else:
            self.fail("Should have raised AstakosClientException exception")

    # ----------------------------------
    # Test the response we get for invalid token
    def _invalid_token(self, pool):
        global auth_url
        token = "skaksaFlBl+fasFdaf24sx"
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token, auth_url, use_pool=pool)
                client.get_user_info()
        except Unauthorized:
            pass
        except Exception:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")
        else:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")

    def test_invalid_token(self):
        """Test _invalid_token without pool"""
        self._invalid_token(False)

    def test_invalid_token_pool(self):
        """Test _invalid_token using pool"""
        self._invalid_token(True)

    #- ---------------------------------
    # Test response for user
    def _auth_user(self, token, user_info, pool):
        global auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token, auth_url, use_pool=pool)
                auth_info = client.get_user_info()
        except:
            self.fail("Shouldn't raise an Exception")
        self.assertEqual(user_info, auth_info)

    def test_auth_user(self):
        """Test _auth_user without pool"""
        global token_1, user_1
        user_info = dict(user_1)
        self._auth_user(token_1, user_info, False)

    def test_auth_user_pool(self):
        """Test _auth_user for User 1 using pool, with usage"""
        global token_1, user_1
        self._auth_user(token_1, user_1, True)

    # ----------------------------------
    # Test retry functionality
    def test_offline_retry(self):
        """Test retry functionality for getUserInfo"""
        global token_1, user_1, auth_url
        _mock_request([_request_offline, _request_offline, _request_ok])
        try:
            with patch_astakosclient([_request_offline, _request_offline,
                                      _request_ok]):
                client = AstakosClient(token_1, auth_url, retry=2)
                auth_info = client.get_user_info()
        except Exception, e:
            self.fail("Shouldn't raise an Exception \"%s\"" % e)
        self.assertEqual(user_1, auth_info)


class TestDisplayNames(unittest.TestCase):
    """Test cases for functions getDisplayNames/getDisplayName"""

    # ----------------------------------
    # Test the response we get for invalid token
    def test_invalid_token(self):
        """Test the response we get for invalid token (without pool)"""
        global user_1, auth_url
        token = "skaksaFlBl+fasFdaf24sx"
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token, auth_url)
                client.get_usernames([user_1['uuid']])
        except Unauthorized:
            pass
        except Exception:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")
        else:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")

    # ----------------------------------
    # Get info for user 1
    def test_username_user_one(self):
        """Test get_username for User One"""
        global token_1, user_1, auth_url
        try:
            with patch_astakosclient([_request_offline, _request_ok]):
                client = AstakosClient(token_1, auth_url,
                                       use_pool=True, retry=2)
                info = client.get_username(user_1['uuid'])
        except:
            self.fail("Shouldn't raise an Exception")
        self.assertEqual(info, user_1['username'])

    # ----------------------------------
    # Get info with wrong uuid
    def test_no_username(self):
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                client.get_username("1234")
        except NoUserName:
            pass
        except:
            self.fail("Should have raised NoDisplayName exception")
        else:
            self.fail("Should have raised NoDisplayName exception")


class TestGetUUIDs(unittest.TestCase):
    """Test cases for functions getUUIDs/getUUID"""

    # ----------------------------------
    # Test the response we get for invalid token
    def test_invalid_token(self):
        """Test the response we get for invalid token (using pool)"""
        global user_1, auth_url
        token = "skaksaFlBl+fasFdaf24sx"
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token, auth_url)
                client.get_uuids([user_1['username']])
        except Unauthorized:
            pass
        except Exception:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")
        else:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")

    # ----------------------------------
    # Get uuid for user 1
    def test_get_uuid_user_two(self):
        """Test get_uuid for User Two"""
        global token_1, user_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url, retry=1)
                catalog = client.get_uuids([user_1['username']])
        except:
            self.fail("Shouldn't raise an Exception")
        self.assertEqual(catalog[user_1['username']], user_1['uuid'])

    # ----------------------------------
    # Get uuid with wrong username
    def test_no_uuid(self):
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                client.get_uuid("1234")
        except NoUUID:
            pass
        except:
            self.fail("Should have raised NoUUID exception")
        else:
            self.fail("Should have raised NoUUID exception")


class TestResources(unittest.TestCase):
    """Test cases for function get_resources"""

    # ----------------------------------
    def test_get_resources(self):
        """Test function call of get_resources"""
        global resources, auth_url, token_1
        try:
            with patch_astakosclient([_request_offline, _request_ok]):
                client = AstakosClient(token_1, auth_url, retry=1)
                result = client.get_resources()
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(resources, result)


class TestQuotas(unittest.TestCase):
    """Test cases for function get_quotas"""

    # ----------------------------------
    def test_get_quotas(self):
        """Test function call of get_quotas"""
        global quotas, token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                result = client.get_quotas()
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(quotas, result)

    # -----------------------------------
    def test_get_quotas_unauthorized(self):
        """Test function call of get_quotas with wrong token"""
        global auth_url
        token = "buahfhsda"
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token, auth_url)
                client.get_quotas()
        except Unauthorized:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raised Unauthorized Exception")


class TestCommissions(unittest.TestCase):
    """Test cases for quota commissions"""

    # ----------------------------------
    def test_issue_commission(self):
        """Test function call of issue_commission"""
        global token_1, commission_request, commission_successful_reqsponse
        global auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                response = client.issue_commission(commission_request)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(response, commission_successful_response['serial'])

    # ----------------------------------
    def test_issue_commission_quota_limit(self):
        """Test function call of issue_commission with limit exceeded"""
        global token_1, commission_request, commission_failure_response
        global auth_url
        new_request = dict(commission_request)
        new_request['provisions'][1]['quantity'] = 520000000
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                client.issue_commission(new_request)
        except QuotaLimit:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raised QuotaLimit Exception")

    # ----------------------------------
    def test_issue_one_commission(self):
        """Test function call of issue_one_commission"""
        global token_1, commission_successful_response, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                response = client.issue_one_commission(
                    "c02f315b-7d84-45bc-a383-552a3f97d2ad",
                    "system", {"cyclades.vm": 1, "cyclades.ram": 30000})
        except Exception as err:
            self.fail("Shouldn't have raised Exception %s" % err)
        self.assertEqual(response, commission_successful_response['serial'])

    # ----------------------------------
    def test_get_pending_commissions(self):
        """Test function call of get_pending_commissions"""
        global token_1, pending_commissions, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                response = client.get_pending_commissions()
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(response, pending_commissions)

    # ----------------------------------
    def test_get_commission_info(self):
        """Test function call of get_commission_info"""
        global token_1, commission_description, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url,
                                       use_pool=True, pool_size=2)
                response = client.get_commission_info(57)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(response, commission_description)

    # ----------------------------------
    def test_get_commission_info_not_found(self):
        """Test function call of get_commission_info with invalid serial"""
        global token_1, auth_url
        _mock_request([_request_ok])
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                client.get_commission_info("57lala")
        except NotFound:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raised NotFound")

    # ----------------------------------
    def test_get_commission_info_without_serial(self):
        """Test function call of get_commission_info without serial"""
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                client.get_commission_info(None)
        except BadValue:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raise BadValue")

    # ----------------------------------
    def test_commision_action(self):
        """Test function call of commision_action with wrong action"""
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                client.commission_action(57, "lala")
        except BadRequest:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raised BadRequest")

    # ----------------------------------
    def test_accept_commission(self):
        """Test function call of accept_commission"""
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                client.accept_commission(57)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)

    # ----------------------------------
    def test_reject_commission(self):
        """Test function call of reject_commission"""
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                client.reject_commission(57)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)

    # ----------------------------------
    def test_accept_commission_not_found(self):
        """Test function call of accept_commission with wrong serial"""
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                client.reject_commission(20)
        except NotFound:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raised NotFound")

    # ----------------------------------
    def test_resolve_commissions(self):
        """Test function call of resolve_commissions"""
        global token_1, auth_url
        try:
            with patch_astakosclient([_request_ok]):
                client = AstakosClient(token_1, auth_url)
                result = client.resolve_commissions([56, 57], [56, 58, 59])
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(result, resolve_commissions_rep)


# ----------------------------
# Run tests
if __name__ == "__main__":
        unittest.main()
