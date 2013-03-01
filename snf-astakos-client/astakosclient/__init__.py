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

import logging
import urlparse
import httplib
import urllib

import simplejson
import objpool.http


# --------------------------------------------------------------------
# Astakos Client Exception
class AstakosClientException(Exception):
    def __init__(self, message, status=0):
        self.message = message
        self.status = status

    def __str__(self):
        return repr(self.message)


# --------------------------------------------------------------------
# Astakos Client Class

def getTokenFromCookie(request, cookie_name):
    """Extract token from the cookie name provided

    Cookie should be in the same form as astakos
    service sets its cookie contents:
        <user_uniq>|<user_token>

    """
    try:
        cookie_content = urllib.unquote(request.COOKIE.get(cookie_name, None))
        return cookie_content.split("|")[1]
    except:
        return None


class AstakosClient():
    """AstakosClient Class Implementation"""

    # ----------------------------------
    def __init__(self, token, astakos_url,
                 use_pool=False, retry=0, logger=None):
        """Intialize AstakosClient Class

        Keyword arguments:
        token       -- user's token (string)
        astakos_url -- i.e https://accounts.example.com (string)
        use_pool    -- use objpool for http requests (boolean)
        retry       -- how many time to retry (integer)
        logger      -- pass a different logger

        """
        if logger is None:
            logger = logging.getLogger("astakosclient")
        logger.debug("Intialize AstakosClient: astakos_url = %s"
                     "use_pool = %s" % (astakos_url, use_pool))

        # Check Input
        if not token:
            m = "Token not given"
            logger.error(m)
            raise ValueError(m)
        if not astakos_url:
            m = "Astakos url not given"
            logger.error(m)
            raise ValueError(m)

        # Check for supported scheme
        p = urlparse.urlparse(astakos_url)
        conn = _scheme_to_class(p.scheme, use_pool)
        if conn is None:
            m = "Unsupported scheme: %s" % p.scheme
            logger.error(m)
            raise ValueError(m)

        # Save token and url
        self.retry = retry
        self.logger = logger
        self.token = token
        self.netloc = p.netloc
        self.scheme = p.scheme
        self.conn = conn

    # ----------------------------------
    def retry(func):
        def decorator(self, *args, **kwargs):
            attemps = 0
            while True:
                try:
                    return func(self, *args, **kwargs)
                except AstakosClientException as err:
                    is_last_attempt = attemps == self.retry
                    if is_last_attempt:
                        raise err
                    if err.status == 401 or err.status == 404:
                        # In case of Unauthorized response
                        # or Not Found return immediately
                        raise err
                    attemps += 1
        return decorator

    # ----------------------------------
    @retry
    def _callAstakos(self, request_path, headers={}, body={}, method="GET"):
        """Make the actual call to Astakos Service"""
        self.logger.debug(
            "Make a %s request to %s with headers %s "
            "and body %s" % (method, request_path, headers, body))

        # Build request's header and body
        kwargs = {}
        kwargs['headers'] = headers
        kwargs['headers']['X-Auth-Token'] = self.token
        if body:
            kwargs['body'] = body
            kwargs['headers'].setdefault(
                'content-type', 'application/octet-stream')
        kwargs['headers'].setdefault('content-length',
                                     len(body) if body else 0)

        # Get the connection object
        conn = self.conn(self.netloc)

        # Send request
        try:
            (data, status) = _doRequest(conn, method, request_path, **kwargs)
        except Exception as err:
            self.logger.error("Failed to send request: %s" % err)
            raise AstakosClientException(str(err))
        finally:
            conn.close()

        # Return
        self.logger.debug("Request returned with status %s" % status)
        if status < 200 or status >= 300:
            raise AstakosClientException(data, status)
        return simplejson.loads(unicode(data))

    # ------------------------
    def authenticate(self, usage=False):
        """Check if user is authenticated Astakos user

        Keyword arguments:
        usage   -- return usage information for user (boolean)

        In case of success return user information (json parsed format).
        Otherwise raise an AstakosClientException.

        """
        auth_path = "/im/authenticate"
        if usage:
            auth_path += "?usage=1"
        return self._callAstakos(auth_path)

    # ----------------------------------
    def getDisplayNames(self, uuids):
        """Return a uuid_catalog dictionary for the given uuids

        Keyword arguments:
        uuids   -- list of user ids (list of strings)

        The returned uuid_catalog is a dictionary with uuids as
        keys and the corresponding user names as values

        """
        req_headers = {'content-type': 'application/json'}
        req_body = simplejson.dumps({'uuids': uuids})
        req_path = "/user_catalogs"

        data = self._callAstakos(req_path, req_headers, req_body, "POST")
        # XXX: check if exists
        return data.get("uuid_catalog")

    def getDisplayName(self, uuid):
        """Return the displayName of a uuid (see getDisplayNames)"""
        if not uuid:
            m = "No uuid was given"
            self.logger.error(m)
            raise ValueError(m)
        uuid_dict = self.getDisplayNames([uuid])
        # XXX: check if exists
        return uuid_dict.get(uuid)


# --------------------------------------------------------------------
# Private functions
def _scheme_to_class(scheme, use_pool):
    """Return the appropriate conn class for given scheme"""
    if scheme == "http":
        if use_pool:
            return _objpoolHttpScheme
        else:
            return httplib.HTTPConnection
    elif scheme == "https":
        if use_pool:
            return _objpoolHttpsScheme
        else:
            return httplib.HTTPSConnection
    else:
        return None


def _objpoolHttpScheme(netloc):
    """Intialize the appropriate objpool.http class"""
    return objpool.http.get_http_connection(netloc, "http")


def _objpoolHttpsScheme(netloc):
    """Intialize the appropriate objpool.http class"""
    return objpool.http.get_http_connection(netloc, "https")


def _doRequest(conn, method, url, **kwargs):
    """The actual request. This function can easily be mocked"""
    conn.request(method, url, **kwargs)
    response = conn.getresponse()
    length = response.getheader('content-length', None)
    data = response.read(length)
    status = int(response.status)
    return (data, status)
