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
import urllib
import hashlib
from copy import copy

import simplejson
from astakosclient.utils import retry, scheme_to_class
from astakosclient.errors import \
    AstakosClientException, Unauthorized, BadRequest, NotFound, Forbidden


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
    def __init__(self, astakos_url, retry=0,
                 use_pool=False, pool_size=8, logger=None):
        """Intialize AstakosClient Class

        Keyword arguments:
        astakos_url -- i.e https://accounts.example.com (string)
        use_pool    -- use objpool for http requests (boolean)
        retry       -- how many time to retry (integer)
        logger      -- pass a different logger

        """
        if logger is None:
            logging.basicConfig(
                format='%(asctime)s [%(levelname)s] %(name)s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                level=logging.INFO)
            logger = logging.getLogger("astakosclient")
        logger.debug("Intialize AstakosClient: astakos_url = %s, "
                     "use_pool = %s" % (astakos_url, use_pool))

        if not astakos_url:
            m = "Astakos url not given"
            logger.error(m)
            raise ValueError(m)

        # Check for supported scheme
        p = urlparse.urlparse(astakos_url)
        conn_class = scheme_to_class(p.scheme, use_pool, pool_size)
        if conn_class is None:
            m = "Unsupported scheme: %s" % p.scheme
            logger.error(m)
            raise ValueError(m)

        # Save astakos_url etc. in our class
        self.retry = retry
        self.logger = logger
        self.netloc = p.netloc
        self.scheme = p.scheme
        self.conn_class = conn_class

    # ----------------------------------
    @retry
    def _callAstakos(self, token, request_path,
                     headers=None, body=None, method="GET"):
        """Make the actual call to Astakos Service"""
        hashed_token = hashlib.sha1()
        hashed_token.update(token)
        self.logger.debug(
            "Make a %s request to %s using token %s "
            "with headers %s and body %s"
            % (method, request_path, hashed_token.hexdigest(), headers, body))

        # Check Input
        if not token:
            m = "Token not given"
            self.logger.error(m)
            raise ValueError(m)
        if headers is None:
            headers = {}
        if body is None:
            body = {}
        if request_path[0] != '/':
            request_path = "/" + request_path

        # Build request's header and body
        kwargs = {}
        kwargs['headers'] = copy(headers)
        kwargs['headers']['X-Auth-Token'] = token
        if body:
            kwargs['body'] = copy(body)
            kwargs['headers'].setdefault(
                'content-type', 'application/octet-stream')
        kwargs['headers'].setdefault('content-length',
                                     len(body) if body else 0)

        # Get the connection object
        conn = self.conn_class(self.netloc)

        # Send request
        try:
            (data, status) = _doRequest(conn, method, request_path, **kwargs)
        except Exception as err:
            self.logger.error("Failed to send request: %s" % repr(err))
            raise AstakosClientException(str(err))
        finally:
            conn.close()

        # Return
        self.logger.debug("Request returned with status %s" % status)
        if status == 400:
            raise BadRequest(data)
        elif status == 401:
            raise Unauthorized(data)
        elif status == 403:
            raise Forbidden(data)
        elif status == 404:
            raise NotFound(data)
        elif status < 200 or status >= 300:
            raise AstakosClientException(data, status)
        return simplejson.loads(unicode(data))

    # ------------------------
    def authenticate(self, token, usage=False):
        """Check if user is authenticated Astakos user

        Keyword arguments:
        token   -- user's token (string)
        usage   -- return usage information for user (boolean)

        In case of success return user information (json parsed format).
        Otherwise raise an AstakosClientException.

        """
        # Send request
        auth_path = "/im/authenticate"
        if usage:
            auth_path += "?usage=1"
        return self._callAstakos(token, auth_path)

    # ----------------------------------
    def _uuidCatalog(self, token, uuids, req_path):
        req_headers = {'content-type': 'application/json'}
        req_body = simplejson.dumps({'uuids': uuids})
        data = self._callAstakos(
            token, req_path, req_headers, req_body, "POST")
        # XXX: check if exists
        return data.get("uuid_catalog")

    def getDisplayNames(self, token, uuids):
        """Return a uuid_catalog dictionary for the given uuids

        Keyword arguments:
        token   -- user's token (string)
        uuids   -- list of user ids (list of strings)

        The returned uuid_catalog is a dictionary with uuids as
        keys and the corresponding user names as values

        """
        req_path = "/user_catalogs"
        return self._uuidCatalog(token, uuids, req_path)

    def getDisplayName(self, token, uuid):
        """Return the displayName of a uuid (see getDisplayNames)"""
        if not uuid:
            m = "No uuid was given"
            self.logger.error(m)
            raise ValueError(m)
        uuid_dict = self.getDisplayNames(token, [uuid])
        # XXX: check if exists
        return uuid_dict.get(uuid)

    def getServiceDisplayNames(self, token, uuids):
        """Return a uuid_catalog dict using a service's token"""
        req_path = "/service/api/user_catalogs"
        return self._uuidCatalog(token, uuids, req_path)

    def getServiceDisplayName(self, token, uuid):
        """Return the displayName of a uuid using a service's token"""
        if not uuid:
            m = "No uuid was given"
            self.logger.error(m)
            raise ValueError(m)
        uuid_dict = self.getServiceDisplayNames(token, [uuid])
        # XXX: check if exists
        return uuid_dict.get(uuid)

    # ----------------------------------
    def _displayNameCatalog(self, token, display_names, req_path):
        req_headers = {'content-type': 'application/json'}
        req_body = simplejson.dumps({'displaynames': display_names})
        data = self._callAstakos(
            token, req_path, req_headers, req_body, "POST")
        # XXX: check if exists
        return data.get("displayname_catalog")

    def getUUIDs(self, token, display_names):
        """Return a displayname_catalog for the given names

        Keyword arguments:
        token           -- user's token (string)
        display_names   -- list of user names (list of strings)

        The returned displayname_catalog is a dictionary with
        the names as keys and the corresponding uuids as values

        """
        req_path = "/user_catalogs"
        return self._displayNameCatalog(token, display_names, req_path)

    def getUUID(self, token, display_name):
        """Return the uuid of a name (see getUUIDs)"""
        if not display_name:
            m = "No display_name was given"
            self.logger.error(m)
            raise ValueError(m)
        name_dict = self.getUUIDs(token, [display_name])
        # XXX: check if exists
        return name_dict.get(display_name)

    def getServiceUUIDs(self, token, display_names):
        """Return a display_name catalog using a service's token"""
        req_path = "/service/api/user_catalogs"
        return self._displayNameCatalog(token, display_names, req_path)

    def getServiceUUID(self, token, display_name):
        """Return the uuid of a name using a service's token"""
        if not display_name:
            m = "No display_name was given"
            self.logger.error(m)
            raise ValueError(m)
        name_dict = self.getServiceUUIDs(token, [display_name])
        # XXX: check if exists
        return name_dict.get(display_name)

    # ----------------------------------
    def getServices(self):
        """Return a list of dicts with the registered services"""
        return self._callAstakos("dummy token", "/im/get_services")


# --------------------------------------------------------------------
# Private functions
# We want _doRequest to be a distinct function
# so that we can replace it during unit tests.
def _doRequest(conn, method, url, **kwargs):
    """The actual request. This function can easily be mocked"""
    conn.request(method, url, **kwargs)
    response = conn.getresponse()
    length = response.getheader('content-length', None)
    data = response.read(length)
    status = int(response.status)
    return (data, status)
