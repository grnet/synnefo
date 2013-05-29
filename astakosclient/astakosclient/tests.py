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

import sys
import socket
import simplejson

import astakosclient
from astakosclient import AstakosClient
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

# ----------------------------
# This functions will be used as mocked requests
def _request_offline(conn, method, url, **kwargs):
    """This request behaves as we were offline"""
    raise socket.gaierror


def _request_status_302(conn, method, url, **kwargs):
    """This request returns 302"""
    message = "FOUND"
    status = 302
    data = '<html>\r\n<head><title>302 Found</title></head>\r\n' \
        '<body bgcolor="white">\r\n<center><h1>302 Found</h1></center>\r\n' \
        '<hr><center>nginx/0.7.67</center>\r\n</body>\r\n</html>\r\n'
    return (message, data, status)


def _request_status_404(conn, method, url, **kwargs):
    """This request returns 404"""
    message = "Not Found"
    status = 404
    data = '<html><head><title>404 Not Found</title></head>' \
        '<body><h1>Not Found</h1><p>The requested URL /foo was ' \
        'not found on this server.</p><hr><address>Apache Server ' \
        'at example.com Port 80</address></body></html>'
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
    if url.startswith(astakosclient.API_AUTHENTICATE):
        return _req_authenticate(conn, method, url, **kwargs)
    elif url.startswith(astakosclient.API_USERCATALOGS):
        return _req_catalogs(conn, method, url, **kwargs)
    elif url.startswith(astakosclient.API_RESOURCES):
        return _req_resources(conn, method, url, **kwargs)
    elif url.startswith(astakosclient.API_QUOTAS):
        return _req_quotas(conn, method, url, **kwargs)
    elif url.startswith(astakosclient.API_COMMISSIONS):
        return _req_commission(conn, method, url, **kwargs)
    elif url.startswith(astakosclient.API_TOKENS):
        return _req_endpoints(conn, method, url, **kwargs)
    else:
        return _request_status_404(conn, method, url, **kwargs)


def _req_authenticate(conn, method, url, **kwargs):
    """Check if user exists and return his profile"""
    global user_1, user_2, token_1, token_2

    # Check input
    if conn.__class__.__name__ != "HTTPSConnection":
        return _request_status_302(conn, method, url, **kwargs)
    if method != "GET":
        return _request_status_400(conn, method, url, **kwargs)
    token = kwargs['headers'].get('X-Auth-Token')
    if token == token_1:
        user = dict(user_1)
    elif token == token_2:
        user = dict(user_2)
    else:
        # No user found
        return _request_status_401(conn, method, url, **kwargs)

    # Return
    if "usage=1" not in url:
        # Strip `usage' key from `user'
        del user['usage']
    return ("", simplejson.dumps(user), 200)


def _req_catalogs(conn, method, url, **kwargs):
    """Return user catalogs"""
    global token_1, token_2, user_1, user_2

    # Check input
    if conn.__class__.__name__ != "HTTPSConnection":
        return _request_status_302(conn, method, url, **kwargs)
    if method != "POST":
        return _request_status_400(conn, method, url, **kwargs)
    token = kwargs['headers'].get('X-Auth-Token')
    if token != token_1 and token != token_2:
        return _request_status_401(conn, method, url, **kwargs)

    # Return
    body = simplejson.loads(kwargs['body'])
    if 'uuids' in body:
        # Return uuid_catalog
        uuids = body['uuids']
        catalogs = {}
        if user_1['uuid'] in uuids:
            catalogs[user_1['uuid']] = user_1['username']
        if user_2['uuid'] in uuids:
            catalogs[user_2['uuid']] = user_2['username']
        return_catalog = {"displayname_catalog": {}, "uuid_catalog": catalogs}
    elif 'displaynames' in body:
        # Return displayname_catalog
        names = body['displaynames']
        catalogs = {}
        if user_1['username'] in names:
            catalogs[user_1['username']] = user_1['uuid']
        if user_2['username'] in names:
            catalogs[user_2['username']] = user_2['uuid']
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
        if url == astakosclient.API_COMMISSIONS:
            # Issue Commission
            # Check if we have enough resources to give
            if body['provisions'][1]['quantity'] > 420000000:
                return ("", simplejson.dumps(commission_failure_response), 413)
            else:
                return \
                    ("", simplejson.dumps(commission_successful_response), 200)
        else:
            # Issue commission action
            serial = url.split('/')[4]
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
        if url == astakosclient.API_COMMISSIONS:
            # Return pending commission
            return ("", simplejson.dumps(pending_commissions), 200)
        else:
            # Return commissions's description
            serial = url[25:]
            if serial == str(57):
                return ("", simplejson.dumps(commission_description), 200)
            else:
                return _request_status_404(conn, method, url, **kwargs)
    else:
        return _request_status_400(conn, method, url, **kwargs)


def _req_endpoints(conn, method, url, **kwargs):
    """Request endpoints"""
    global token_1, endpoints

    # Check input
    if conn.__class__.__name__ != "HTTPSConnection":
        return _request_status_302(conn, method, url, **kwargs)

    token_head = kwargs['headers'].get('X-Auth-Token')
    if url == astakosclient.API_TOKENS:
        if method != "POST":
            return _request_status_400(conn, method, url, **kwargs)
        body = simplejson.loads(kwargs['body'])
        token = body['auth']['token']['id']
        if token != token_1:
            return _request_status_401(conn, method, url, **kwargs)
        # Return
        return ("", simplejson.dumps(user_info_endpoints), 200)

    else:
        if method != "GET":
            return _request_status_400(conn, method, url, **kwargs)
        url_split = url[len(astakosclient.API_TOKENS):].split('/')
        token_url = url_split[1]
        if token_head != token_url:
            return _request_status_403(conn, method, url, **kwargs)
        if token_url != token_1:
            return _request_status_401(conn, method, url, **kwargs)
        # Return
        return ("", simplejson.dumps(endpoints), 200)


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


# ----------------------------
# Local users
token_1 = "skzleaFlBl+fasFdaf24sx=="
user_1 = \
    {"username": "user1@example.com",
     "auth_token_created": 1359386939000,
     "name": "Example User One",
     "email": ["user1@example.com"],
     "auth_token_expires": 1361978939000,
     "id": 108,
     "uuid": "73917abc-abcd-477e-a1f1-1763abcdefab",
     "usage": [
         {"currValue": 42949672960,
          "display_name": "System Disk",
          "name": "cyclades.disk"},
         {"currValue": 4,
          "display_name": "CPU",
          "name": "cyclades.cpu"},
         {"currValue": 4294967296,
          "display_name": "RAM",
          "name": "cyclades.ram"},
         {"currValue": 3,
          "display_name": "VM",
          "name": "cyclades.vm"},
         {"currValue": 0,
          "display_name": "private network",
          "name": "cyclades.network.private"},
         {"currValue": 152,
          "display_name": "Storage Space",
          "name": "pithos+.diskspace"}]}

token_2 = "fasdfDSFdf98923DF+sdfk=="
user_2 = \
    {"username": "user2@example.com",
     "auth_token_created": 1358386938997,
     "name": "Example User Two",
     "email": ["user1@example.com"],
     "auth_token_expires": 1461998939000,
     "id": 109,
     "uuid": "73917bca-1234-5678-a1f1-1763abcdefab",
     "usage": [
         {"currValue": 68719476736,
          "display_name": "System Disk",
          "name": "cyclades.disk"},
         {"currValue": 1,
          "display_name": "CPU",
          "name": "cyclades.cpu"},
         {"currValue": 1073741824,
          "display_name": "RAM",
          "name": "cyclades.ram"},
         {"currValue": 2,
          "display_name": "VM",
          "name": "cyclades.vm"},
         {"currValue": 1,
          "display_name": "private network",
          "name": "cyclades.network.private"},
         {"currValue": 2341634510,
          "display_name": "Storage Space",
          "name": "pithos+.diskspace"}]}

resources = {
    "cyclades.vm": {
        "unit": None,
        "description": "Number of virtual machines",
        "service": "cyclades"},
    "cyclades.ram": {
        "unit": "bytes",
        "description": "Virtual machine memory",
        "service": "cyclades"}}

endpoints = {
    "endpoints": [
        {"name": "cyclades",
         "region": "cyclades",
         "internalURL": "https://node1.example.com/ui/",
         "adminURL": "https://node1.example.com/v1/",
         "type": None,
         "id": 5,
         "publicURL": "https://node1.example.com/ui/"},
        {"name": "pithos",
         "region": "pithos",
         "internalURL": "https://node2.example.com/ui/",
         "adminURL": "https://node2.example.com/v1",
         "type": None,
         "id": 6,
         "publicURL": "https://node2.example.com/ui/"}],
    "endpoint_links": [
        {"href": "/astakos/api/tokens/0000/endpoints?marker=4&limit=10000",
         "rel": "next"}]}

user_info_endpoints = \
    {'serviceCatalog': [
        {'endpoints': [{
            'SNF:uiURL': 'https://node1.example.com/ui/',
            'adminURL': 'https://node1.example.com/v1',
            'internalUrl': 'https://node1.example.com/v1',
            'publicURL': 'https://node1.example.com/v1',
            'region': 'cyclades'}],
         'name': 'cyclades',
         'type': 'compute'},
        {'endpoints': [{
            'SNF:uiURL': 'https://node2.example.com/ui/',
            'adminURL': 'https://node2.example.com/v1',
            'internalUrl': 'https://node2.example.com/v1',
            'publicURL': 'https://node2.example.com/v1',
            'region': 'pithos'}],
         'name': 'pithos',
         'type': 'storage'}],
     'token': {
         'expires': '2013-06-19T15:23:59.975572+00:00',
         'id': token_1,
         'tenant': {
             'id': user_1,
             'name': 'Firstname Lastname'}},
     'user': {
         'id': user_1,
         'name': 'Firstname Lastname',
         'roles': [{'id': 1, 'name': 'default'}],
         'roles_links': []}}

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


# --------------------------------------------------------------------
# The actual tests

class TestCallAstakos(unittest.TestCase):
    """Test cases for function _callAstakos"""

    # ----------------------------------
    # Test the response we get if we don't have internet access
    def _offline(self, pool):
        global token_1
        _mock_request([_request_offline])
        try:
            client = AstakosClient("https://example.com", use_pool=pool)
            client._call_astakos(token_1, astakosclient.API_AUTHENTICATE)
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
        token = "skaksaFlBl+fasFdaf24sx=="
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com", use_pool=pool)
            client._call_astakos(token, astakosclient.API_AUTHENTICATE)
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
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com", use_pool=pool)
            client._call_astakos(token_1, "/astakos/api/misspelled")
        except NotFound:
            pass
        except Exception:
            self.fail("Should have returned 404 (Not Found)")
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
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("ftp://example.com", use_pool=pool)
            client._call_astakos(token_1, astakosclient.API_AUTHENTICATE)
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
        _mock_request([_request_ok])
        try:
            client = AstakosClient("http://example.com", use_pool=pool)
            client._call_astakos(token_1, astakosclient.API_AUTHENTICATE)
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
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com", use_pool=pool)
            client._call_astakos(
                token_1, astakosclient.API_AUTHENTICATE, method="POST")
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
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com", use_pool=pool)
            client._call_astakos(token_1, astakosclient.API_USERCATALOGS)
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
        global token_1
        _mock_request([_request_offline])
        try:
            client = AstakosClient("https://example.com", retry=3)
            client.get_user_info(token_1)
        except AstakosClientException:
            pass
        else:
            self.fail("Should have raised AstakosClientException exception")

    # ----------------------------------
    # Test the response we get for invalid token
    def _invalid_token(self, pool):
        token = "skaksaFlBl+fasFdaf24sx=="
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com", use_pool=pool)
            client.get_user_info(token)
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
    # Test response for user 1
    def _auth_user(self, token, user_info, usage, pool):
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com", use_pool=pool)
            auth_info = client.get_user_info(token, usage=usage)
        except:
            self.fail("Shouldn't raise an Exception")
        self.assertEqual(user_info, auth_info)

    def test_auth_user_one(self):
        """Test _auth_user for User 1 without pool, without usage"""
        global token_1, user_1
        user_info = dict(user_1)
        del user_info['usage']
        self._auth_user(token_1, user_info, False, False)

    def test_auth_user_one_usage(self):
        """Test _auth_user for User 1 without pool, with usage"""
        global token_1, user_1
        self._auth_user(token_1, user_1, True, False)

    def test_auth_user_one_usage_pool(self):
        """Test _auth_user for User 1 using pool, with usage"""
        global token_1, user_1
        self._auth_user(token_1, user_1, True, True)

    def test_auth_user_two(self):
        """Test _auth_user for User 2 without pool, without usage"""
        global token_2, user_2
        user_info = dict(user_2)
        del user_info['usage']
        self._auth_user(token_2, user_info, False, False)

    def test_auth_user_two_usage(self):
        """Test _auth_user for User 2 without pool, with usage"""
        global token_2, user_2
        self._auth_user(token_2, user_2, True, False)

    def test_auth_user_two_usage_pool(self):
        """Test _auth_user for User 2 using pool, with usage"""
        global token_2, user_2
        self._auth_user(token_2, user_2, True, True)

    # ----------------------------------
    # Test retry functionality
    def test_offline_retry(self):
        """Test retry functionality for getUserInfo"""
        global token_1, user_1
        _mock_request([_request_offline, _request_offline, _request_ok])
        try:
            client = AstakosClient("https://example.com", retry=2)
            auth_info = client.get_user_info(token_1, usage=True)
        except:
            self.fail("Shouldn't raise an Exception")
        self.assertEqual(user_1, auth_info)


class TestDisplayNames(unittest.TestCase):
    """Test cases for functions getDisplayNames/getDisplayName"""

    # ----------------------------------
    # Test the response we get for invalid token
    def test_invalid_token(self):
        """Test the response we get for invalid token (without pool)"""
        global user_1
        token = "skaksaFlBl+fasFdaf24sx=="
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.get_usernames(token, [user_1['uuid']])
        except Unauthorized:
            pass
        except Exception:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")
        else:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")

    # ----------------------------------
    # Get Info for both users
    def test_usernames(self):
        """Test get_usernames with both users"""
        global token_1, user_1, user_2
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            catalog = client.get_usernames(
                token_1, [user_1['uuid'], user_2['uuid']])
        except:
            self.fail("Shouldn't raise an Exception")
        self.assertEqual(catalog[user_1['uuid']], user_1['username'])
        self.assertEqual(catalog[user_2['uuid']], user_2['username'])

    # ----------------------------------
    # Get info for user 1
    def test_username_user_one(self):
        """Test get_username for User One"""
        global token_2, user_1
        _mock_request([_request_offline, _request_ok])
        try:
            client = AstakosClient(
                "https://example.com", use_pool=True, retry=2)
            info = client.get_username(token_2, user_1['uuid'])
        except:
            self.fail("Shouldn't raise an Exception")
        self.assertEqual(info, user_1['username'])

    # ----------------------------------
    # Get info with wrong uuid
    def test_no_username(self):
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.get_username(token_1, "1234")
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
        global user_1
        token = "skaksaFlBl+fasFdaf24sx=="
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.get_uuids(token, [user_1['username']])
        except Unauthorized:
            pass
        except Exception:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")
        else:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")

    # ----------------------------------
    # Get info for both users
    def test_uuids(self):
        """Test get_uuids with both users"""
        global token_1, user_1, user_2
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            catalog = client.get_uuids(
                token_1, [user_1['username'], user_2['username']])
        except:
            self.fail("Shouldn't raise an Exception")
        self.assertEqual(catalog[user_1['username']], user_1['uuid'])
        self.assertEqual(catalog[user_2['username']], user_2['uuid'])

    # ----------------------------------
    # Get uuid for user 2
    def test_get_uuid_user_two(self):
        """Test get_uuid for User Two"""
        global token_1, user_2
        _mock_request([_request_offline, _request_ok])
        try:
            client = AstakosClient("https://example.com", retry=1)
            info = client.get_uuid(token_2, user_1['username'])
        except:
            self.fail("Shouldn't raise an Exception")
        self.assertEqual(info, user_1['uuid'])

    # ----------------------------------
    # Get uuid with wrong username
    def test_no_uuid(self):
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.get_uuid(token_1, "1234")
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
        global resources
        _mock_request([_request_offline, _request_ok])
        try:
            client = AstakosClient("https://example.com", retry=1)
            result = client.get_resources()
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(resources, result)


class TestQuotas(unittest.TestCase):
    """Test cases for function get_quotas"""

    # ----------------------------------
    def test_get_quotas(self):
        """Test function call of get_quotas"""
        global quotas, token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            result = client.get_quotas(token_1)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(quotas, result)

    # -----------------------------------
    def test_get_quotas_unauthorized(self):
        """Test function call of get_quotas with wrong token"""
        global token_2
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.get_quotas(token_2)
        except Unauthorized:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raised Unauthorized Exception")

    # ----------------------------------
    def test_get_quotas_without_token(self):
        """Test function call of get_quotas without token"""
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.get_quotas(None)
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
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            response = client.issue_commission(token_1, commission_request)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(response, commission_successful_response['serial'])

    # ----------------------------------
    def test_issue_commission_quota_limit(self):
        """Test function call of issue_commission with limit exceeded"""
        global token_1, commission_request, commission_failure_response
        _mock_request([_request_ok])
        new_request = dict(commission_request)
        new_request['provisions'][1]['quantity'] = 520000000
        try:
            client = AstakosClient("https://example.com")
            client.issue_commission(token_1, new_request)
        except QuotaLimit:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raised QuotaLimit Exception")

    # ----------------------------------
    def test_issue_one_commission(self):
        """Test function call of issue_one_commission"""
        global token_1, commission_successful_response
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            response = client.issue_one_commission(
                token_1, "c02f315b-7d84-45bc-a383-552a3f97d2ad",
                "system", {"cyclades.vm": 1, "cyclades.ram": 30000})
        except Exception as err:
            self.fail("Shouldn't have raised Exception %s" % err)
        self.assertEqual(response, commission_successful_response['serial'])

    # ----------------------------------
    def test_get_pending_commissions(self):
        """Test function call of get_pending_commissions"""
        global token_1, pending_commissions
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            response = client.get_pending_commissions(token_1)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(response, pending_commissions)

    # ----------------------------------
    def test_get_commission_info(self):
        """Test function call of get_commission_info"""
        global token_1, commission_description
        _mock_request([_request_ok])
        try:
            client = \
                AstakosClient("https://example.com", use_pool=True, pool_size=2)
            response = client.get_commission_info(token_1, 57)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(response, commission_description)

    # ----------------------------------
    def test_get_commission_info_not_found(self):
        """Test function call of get_commission_info with invalid serial"""
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.get_commission_info(token_1, "57lala")
        except NotFound:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raised NotFound")

    # ----------------------------------
    def test_get_commission_info_without_serial(self):
        """Test function call of get_commission_info without serial"""
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.get_commission_info(token_1, None)
        except BadValue:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raise BadValue")

    # ----------------------------------
    def test_commision_action(self):
        """Test function call of commision_action with wrong action"""
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.commission_action(token_1, 57, "lala")
        except BadRequest:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raised BadRequest")

    # ----------------------------------
    def test_accept_commission(self):
        """Test function call of accept_commission"""
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.accept_commission(token_1, 57)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)

    # ----------------------------------
    def test_reject_commission(self):
        """Test function call of reject_commission"""
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.reject_commission(token_1, 57)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)

    # ----------------------------------
    def test_accept_commission_not_found(self):
        """Test function call of accept_commission with wrong serial"""
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.reject_commission(token_1, 20)
        except NotFound:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raised NotFound")

    # ----------------------------------
    def test_resolve_commissions(self):
        """Test function call of resolve_commissions"""
        global token_1
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            result = client.resolve_commissions(token_1, [56, 57], [56, 58, 59])
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(result, resolve_commissions_rep)


class TestEndPoints(unittest.TestCase):
    """Test cases for endpoints requests"""

    # ----------------------------------
    def test_get_endpoints(self):
        """Test function call of get_endpoints"""
        global token_1, endpoints
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            response = client.get_endpoints(token_1)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(response, endpoints)

    # ----------------------------------
    def test_get_endpoints_wrong_token(self):
        """Test function call of get_endpoints with wrong token"""
        global token_2, endpoints
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            client.get_endpoints(token_2, marker=2, limit=100)
        except Unauthorized:
            pass
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        else:
            self.fail("Should have raised Unauthorized Exception")

    # ----------------------------------
    def test_get_user_info_with_endpoints(self):
        """Test function call of get_user_info_with_endpoints"""
        global token_1, user_info_endpoints
        _mock_request([_request_ok])
        try:
            client = AstakosClient("https://example.com")
            response = client.get_user_info_with_endpoints(token_1)
        except Exception as err:
            self.fail("Shouldn't raise Exception %s" % err)
        self.assertEqual(response, user_info_endpoints)


# ----------------------------
# Run tests
if __name__ == "__main__":
    unittest.main()
