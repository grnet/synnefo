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

from httplib import HTTPConnection, HTTPSConnection
from contextlib import closing

import simplejson
from objpool.http import PooledHTTPConnection
from astakosclient.errors import AstakosClientException, BadValue


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
                self.logger.warning("AstakosClient request failed..retrying")
                attemps += 1
    return decorator


def scheme_to_class(scheme, use_pool, pool_size):
    """Return the appropriate conn class for given scheme"""
    def _objpool(netloc):
        return PooledHTTPConnection(
            netloc=netloc, scheme=scheme, size=pool_size)

    def _http_connection(netloc):
        return closing(HTTPConnection(netloc))

    def _https_connection(netloc):
        return closing(HTTPSConnection(netloc))

    if scheme == "http":
        if use_pool:
            return _objpool
        else:
            return _http_connection
    elif scheme == "https":
        if use_pool:
            return _objpool
        else:
            return _https_connection
    else:
        return None


def parse_request(request, logger):
    """Parse request with simplejson to convert it to string"""
    try:
        return simplejson.dumps(request)
    except Exception as err:
        m = "Cannot parse request \"%s\" with simplejson: %s" \
            % (request, str(err))
        logger.error(m)
        raise BadValue(m)


def check_input(function_name, logger, **kwargs):
    """Check if given arguments are not None"""
    for i in kwargs:
        if kwargs[i] is None:
            m = "in " + function_name + ": " + str(i) + " parameter not given"
            logger.error(m)
            raise BadValue(m)
