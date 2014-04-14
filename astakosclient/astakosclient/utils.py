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

"""
Astakos Client utility module
"""

from httplib import HTTPConnection, HTTPSConnection
from contextlib import closing

import simplejson
from objpool.http import PooledHTTPConnection
from astakosclient.errors import AstakosClientException, BadValue


def retry_dec(func):
    """Class Method Decorator"""
    def decorator(self, *args, **kwargs):
        """Retry `self.retry' times if connection fails"""
        attemps = 0
        while True:
            try:
                return func(self, *args, **kwargs)
            except AstakosClientException as err:
                is_last_attempt = attemps == self.retry
                if is_last_attempt:
                    raise err
                if err.status == 401 or \
                   err.status == 404 or \
                   err.status == 413:
                    # In case of Unauthorized response
                    # or Not Found or Request Entity Too Large
                    # return immediately
                    raise err
                self.logger.warning("AstakosClient request failed..retrying")
                attemps += 1
    return decorator


def scheme_to_class(scheme, use_pool, pool_size):
    """Return the appropriate conn class for given scheme"""
    def _objpool(netloc):
        """Helper function to return a PooledHTTPConnection object"""
        return PooledHTTPConnection(
            netloc=netloc, scheme=scheme, size=pool_size)

    def _http_connection(netloc):
        """Helper function to return an HTTPConnection object"""
        return closing(HTTPConnection(netloc))

    def _https_connection(netloc):
        """Helper function to return an HTTPSConnection object"""
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
        msg = "Cannot parse request \"%s\" with simplejson: %s" \
              % (request, str(err))
        logger.error(msg)
        raise BadValue(msg)


def check_input(function_name, logger, **kwargs):
    """Check if given arguments are not None"""
    for i in kwargs:
        if kwargs[i] is None:
            msg = "in " + function_name + ": " + \
                  str(i) + " parameter not given"
            logger.error(msg)
            raise BadValue(msg)


def join_urls(url_a, url_b):
    """Join_urls from synnefo.lib"""
    return url_a.rstrip("/") + "/" + url_b.lstrip("/")
