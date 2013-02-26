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
# Private functions
def _scheme_to_class(scheme):
    """Return the appropriate httplib class for given scheme"""
    if scheme == "http":
        return httplib.HTTPConnection
    elif scheme == "https":
        return httplib.HTTPSConnection
    else:
        return None


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
        conn.request(method, p.path + '?' + p.query, **kwargs)
        response = conn.getresponse()
        length = response.getheader('content-length', None)
        data = response.read(length)
        status = int(response.status)
    except httplib.HTTPException as err:
        logger.error("Failed to send request: %s" % err)
        raise
    finally:
        conn.close()

    # Return
    logger.debug("Request returned with status %s" % status)
    if status < 200 or status >= 300:
        raise Exception(data, status)
    return simplejson.loads(unicode(data))
