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

import simplejson
import objpool.http


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Astakos client API

# A simple retry decorator
def retry(howmany):
    def decorator(func):
        def f(*args, **kwargs):
            attemps = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    is_last_attempt = attemps == howmany - 1
                    if is_last_attempt:
                        raise e
                    if e.args:
                        status = e[0]
                        # In case of Unauthorized response
                        # or Not Found return immediately
                        if status == 401 or status == 404:
                            raise e
                    attemps += 1
        return f
    return decorator


# ----------------------------
# Authenticate
@retry(3)
def authenticate(token, astakos_url, usage=False, use_pool=False):
    """Check if user is an authenticated Astakos user

    Keyword arguments:
    token       -- user's token (string)
    astakos_url -- i.e https://accounts.example.com (string)
    usage       -- return usage information for user (boolean)
    use_pool    -- use objpool for http requests (boolean)

    In case of success return user informations (json parsed format).
    Otherwise raise an Exception.

    """
    if not token:
        logger.error("authenticate: No token was given")
        return None
    authentication_url = urlparse.urljoin(astakos_url, "/im/authenticate")
    if usage:
        authentication_url += "?usage=1,"
    return _callAstakos(token, authentication_url, use_pool=use_pool)


# ----------------------------
# Display Names
@retry(3)
def getDisplayNames(token, uuids, astakos_url, use_pool=False):
    """Return a uuid_catalog dictionary for the given uuids

    Keyword arguments:
    token       -- user's token (string)
    uuids       -- list of user ids (list of strings)
    astakos_url -- i.e https://accounts.example.com (string)
    use_pool    -- use objpool for http requests (boolean)

    The returned uuid_catalog is a dictionary with uuids as
    keys and the corresponding user names as values

    """
    if not token:
        logger.error("getDisplayNames: No token was give")
        return None
    req_headers = {'content-type': 'application/json'}
    req_body = simplejson.dumps({'uuids': uuids})
    req_url = urlparse.urljoin(astakos_url, "/user_catalogs")

    data = _callAstakos(token, req_url, headers=req_headers,
                        body=req_body, method="POST", use_pool=use_pool)
    return data.get("uuid_catalog")


def getDisplayName(token, uuid, astakos_url, use_pool=False):
    """Return the displayname of a uuid (see getDisplayNames)"""
    if not token:
        logger.error("getDisplayName: No token was give")
        return None
    if not uuid:
        logger.error("getDiplayName: No uuid was given")
        return None
    uuid_dict = getDisplayNames(token, [uuid], astakos_url, use_pool)
    return uuid_dict.get(uuid)


# --------------------------------------------------------------------
# Private functions
def _scheme_to_class(scheme):
    """Return the appropriate httplib class for given scheme"""
    if scheme == "http":
        return httplib.HTTPConnection
    elif scheme == "https":
        return httplib.HTTPSConnection
    else:
        return None


def _doRequest(conn, method, url, **kwargs):
    """The actual request. This function can easily be mocked"""
    conn.request(method, url, **kwargs)
    response = conn.getresponse()
    length = response.getheader('content-length', None)
    data = response.read(length)
    status = int(response.status)
    return (status, data)


def _callAstakos(token, url, headers={}, body=None,
                 method='GET', use_pool=False):
    """Make the actual call to astakos service"""
    logger.debug("Make a %s request to %s with token %s, "
                 "headers %s and body %s, %s using the pool" %
                 (method, url, token, headers, body,
                     "not" if not use_pool else ""))

    # Build request's header and body
    kwargs = {}
    kwargs['headers'] = headers
    kwargs['headers']['X-Auth-Token'] = token
    if body:
        kwargs['body'] = body
        kwargs['headers'].setdefault(
            'content-type', 'application/octet-stream')
    kwargs['headers'].setdefault('content-length', len(body) if body else 0)

    # Check for supported scheme
    p = urlparse.urlparse(url)
    connection_class = _scheme_to_class(p.scheme)
    if connection_class is None:
        m = "Unsupported scheme: %s" % p.scheme
        logger.error(m)
        raise ValueError(m)

    # Get connection object
    if use_pool:
        conn = objpool.http.get_http_connection(p.netloc, p.scheme)
    else:
        conn = connection_class(p.netloc)

    # Send request
    try:
        request_url = p.path + '?' + p.query
        (status, data) = _doRequest(conn, method, request_url, **kwargs)
    except httplib.HTTPException as err:
        logger.error("Failed to send request: %s" % err)
        raise
    finally:
        conn.close()

    # Return
    logger.debug("Request returned with status %s" % status)
    if status < 200 or status >= 300:
        raise Exception(status, data)
    return simplejson.loads(unicode(data))
