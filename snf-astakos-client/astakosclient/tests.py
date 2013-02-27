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

import astakosclient

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
def _requestOffline(conn, method, url, **kwargs):
    """This request behaves as we were offline"""
    raise socket.gaierror


def _requestStatus302(conn, method, url, **kwargs):
    """This request returns 302"""
    status = 302
    data = '<html>\r\n<head><title>302 Found</title></head>\r\n' \
        '<body bgcolor="white">\r\n<center><h1>302 Found</h1></center>\r\n' \
        '<hr><center>nginx/0.7.67</center>\r\n</body>\r\n</html>\r\n'
    return (status, data)


def _requestStatus404(conn, method, url, **kwargs):
    """This request returns 404"""
    status = 404
    data = '<html><head><title>404 Not Found</title></head>' \
        '<body><h1>Not Found</h1><p>The requested URL /foo was ' \
        'not found on this server.</p><hr><address>Apache Server ' \
        'at example.com Port 80</address></body></html>'
    return (status, data)


def _requestStatus401(conn, method, url, **kwargs):
    """This request returns 401"""
    status = 401
    data = "Invalid X-Auth-Token\n"
    return (status, data)


def _requestStatus400(conn, method, url, **kwargs):
    """This request returns 400"""
    status = 400
    data = "Method not allowed.\n"
    return (status, data)


def _requestOk(conn, method, url, **kwargs):
    """This request behaves like original Astakos does"""
    if url[0:17] == "/im/authenticate?":
        return _reqAuthenticate(conn, method, url, **kwargs)
    elif url[0:15] == "/user_catalogs?":
        return _reqCatalogs(conn, method, url, **kwargs)
    else:
        return _requestStatus404(conn, method, url, **kwargs)


def _reqAuthenticate(conn, method, url, **kwargs):
    """Check if user exists and return his profile"""
    global user_1, user_2

    if conn.__class__.__name__ != "HTTPSConnection":
        return _requestStatus302(conn, method, url, **kwargs)

    if method != "GET":
        return _requestStatus400(conn, method, url, **kwargs)

    token = kwargs['headers']['X-Auth-Token']
    if token == token_1:
        user = user_1
    elif token == token_2:
        user = user_2
    else:
        # No user found
        return _requestStatus401(conn, method, url, **kwargs)

    if "usage=1" in url:
        return (200, user)
    else:
        # Strip `usage' key from `user'
        del user['usage']
        return user


def _reqCatalogs(conn, method, url, **kwargs):
    """Return user catalogs"""
    # XXX: not implemented yet
    return [{}]


# ----------------------------
# Mock the actual _doRequest
def _mockRequest(new_requests):
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
    astakosclient._doRequest = _mock


# ----------------------------
# Local users
token_1 = "skzleaFlBl+fasFdaf24sx=="
user_1 = {"username": "user1@example.com",
          "auth_token_created": 1359386939000,
          "name": "Example User One",
          "email": ["user1@example.com"],
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
               "name": "pithos+.diskspace"}],
          "auth_token_expires": 1361978939000,
          "id": 108,
          "uuid": "73917abc-abcd-477e-a1f1-1763abcdefab"}

token_2 = "fasdfDSFdf98923DF+sdfk=="
user_2 = {"username": "user2@example.com",
          "auth_token_created": 1358386938997,
          "name": "Example User Two",
          "email": ["user1@example.com"],
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
               "name": "pithos+.diskspace"}],
          "auth_token_expires": 1461998939000,
          "id": 109,
          "uuid": "73917bca-1234-5678-a1f1-1763abcdefab"}


# --------------------------------------------------------------------
# The actual tests

class TestCallAstakos(unittest.TestCase):
    """Test cases for function _callAstakos"""

    # ----------------------------------
    # Test the response we get if we don't have internet access
    def _offline(self, pool):
        global token_1
        _mockRequest([_requestOffline])
        try:
            astakosclient._callAstakos(
                token_1, "https://127.0.0.1/im/authenticate", use_pool=pool)
        except socket.error:
            pass
        except Exception:
            self.fail("Should have raised socket exception")
        else:
            self.fail("Shouldn't succeed")

    def test_Offline(self):
        """Test _offline without pool"""
        self._offline(False)

    def test_OfflinePool(self):
        """Test _offline using pool"""
        self._offline(True)

    # ----------------------------------
    # Test the response we get if we send invalid token
    def _invalidToken(self, pool):
        token = "skaksaFlBl+fasFdaf24sx=="
        _mockRequest([_requestOk])
        try:
            astakosclient._callAstakos(
                token, "https://127.0.0.1/im/authenticate", use_pool=pool)
        except Exception as (status, data):
            if status != 401:
                self.fail("Should have returned 401 (Invalid X-Auth-Token)")
        else:
            self.fail("Should have returned 401 (Invalid X-Auth-Token)")

    def test_InvalidToken(self):
        """Test _invalidToken without pool"""
        self._invalidToken(False)

    def test_InvalidTokenPool(self):
        """Test _invalidToken using pool"""
        self._invalidToken(True)

    # ----------------------------------
    # Test the response we get if we send invalid url
    def _invalidUrl(self, pool):
        global token_1
        _mockRequest([_requestOk])
        try:
            astakosclient._callAstakos(
                token_1, "https://127.0.0.1/im/misspelled", use_pool=pool)
        except Exception as (status, data):
            if status != 404:
                self.fail("Should have returned 404 (Not Found)")
        else:
            self.fail("Should have returned 404 (Not Found)")

    def test_InvalidUrl(self):
        """Test _invalidUrl without pool"""
        self._invalidUrl(False)

    def test_invalidUrlPool(self):
        """Test _invalidUrl using pool"""
        self._invalidUrl(True)

    # ----------------------------------
    # Test the response we get if we use an unsupported scheme
    def _unsupportedScheme(self, pool):
        global token_1
        _mockRequest([_requestOk])
        try:
            astakosclient._callAstakos(
                token_1, "ftp://127.0.0.1/im/authenticate", use_pool=pool)
        except ValueError:
            pass
        except Exception:
            self.fail("Should have raise ValueError Exception")
        else:
            self.fail("Should have raise ValueError Exception")

    def test_UnsupportedScheme(self):
        """Test _unsupportedScheme without pool"""
        self._unsupportedScheme(False)

    def test_UnsupportedSchemePool(self):
        """Test _unsupportedScheme using pool"""
        self._unsupportedScheme(True)

    # ----------------------------------
    # Test the response we get if we use http instead of https
    def _httpScheme(self, pool):
        global token_1
        _mockRequest([_requestOk])
        try:
            astakosclient._callAstakos(
                token_1, "http://127.0.0.1/im/authenticate", use_pool=pool)
        except Exception as (status, data):
            if status != 302:
                self.fail("Should have returned 302 (Found)")
        else:
            self.fail("Should have returned 302 (Found)")

    def test_HttpScheme(self):
        """Test _httpScheme without pool"""
        self._httpScheme(False)

    def test_HttpSchemePool(self):
        """Test _httpScheme using pool"""
        self._httpScheme(True)

    # ----------------------------------
    # Test the response we get if we use authenticate with POST
    def _postAuthenticate(self, pool):
        global token_1
        _mockRequest([_requestOk])
        try:
            astakosclient._callAstakos(
                token_1, "https://127.0.0.1/im/authenticate",
                use_pool=pool, method="POST")
        except Exception as (status, data):
            if status != 400:
                self.fail("Should have returned 400 (Method not allowed)")
        else:
            self.fail("Should have returned 400 (Method not allowed)")

    def test_PostAuthenticate(self):
        """Test _postAuthenticate without pool"""
        self._postAuthenticate(False)

    def test_PostAuthenticatePool(self):
        """Test _postAuthenticate using pool"""
        self._postAuthenticate(True)


# ----------------------------
# Run tests
if __name__ == "__main__":
    unittest.main()
