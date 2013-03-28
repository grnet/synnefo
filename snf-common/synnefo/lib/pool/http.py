# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from synnefo.lib.pool import ObjectPool, PooledObject
from select import select

from httplib import (
    HTTPConnection as http_class,
    HTTPSConnection as https_class,
    ResponseNotReady,
)

from threading import Lock

import logging

log = logging.getLogger(__name__)

_pools = {}
_pools_mutex = Lock()

default_pool_size = 100
USAGE_LIMIT = 1000


def init_http_pooling(size):
    global default_pool_size
    default_pool_size = size


class HTTPConnectionPool(ObjectPool):

    _scheme_to_class = {
        'http': http_class,
        'https': https_class,
    }

    def __init__(self, scheme, netloc, size=None):
        log.debug("INIT-POOL: Initializing pool of size %d, scheme: %s, "
                  "netloc: %s", size, scheme, netloc)
        ObjectPool.__init__(self, size=size)

        connection_class = self._scheme_to_class.get(scheme, None)
        if connection_class is None:
            m = 'Unsupported scheme: %s' % (scheme,)
            raise ValueError(m)

        self.connection_class = connection_class
        self.scheme = scheme
        self.netloc = netloc

    def _pool_create(self):
        log.debug("CREATE-HTTP-BEFORE from pool %r", self)
        conn = self.connection_class(self.netloc)
        conn._pool_use_counter = USAGE_LIMIT
        return conn

    def _pool_verify(self, conn):
        log.debug("VERIFY-HTTP")
        if conn is None:
            return False
        sock = conn.sock
        if sock is None:
            return True
        if select((conn.sock,), (), (), 0)[0]:
            return False
        return True

    def _pool_cleanup(self, conn):
        log.debug("CLEANUP-HTTP")
        # every connection can be used a finite number of times
        conn._pool_use_counter -= 1

        # see httplib source for connection states documentation
        conn_state = conn._HTTPConnection__state
        if (conn._pool_use_counter > 0 and conn_state == "Idle"):
            try:
                conn.getresponse()
            except ResponseNotReady:
                log.debug("CLEANUP-HTTP: Not closing connection. Will reuse.")
                return False

        log.debug("CLEANUP-HTTP: Closing connection. Will not reuse.")
        conn.close()
        return True


class PooledHTTPConnection(PooledObject):

    _pool_log_prefix = "HTTP"
    _pool_class = HTTPConnectionPool

    def __init__(self, netloc, scheme='http', pool=None, **kw):
        kw['netloc'] = netloc
        kw['scheme'] = scheme
        kw['pool'] = pool
        super(PooledHTTPConnection, self).__init__(**kw)

    def get_pool(self):
        kwargs = self._pool_kwargs
        pool = kwargs.pop('pool', None)
        if pool is not None:
            return pool

        # pool was not given, find one from the global registry
        scheme = kwargs['scheme']
        netloc = kwargs['netloc']
        size = kwargs.get('size', default_pool_size)
        # ensure distinct pools for every (scheme, netloc) combination
        key = (scheme, netloc)
        with _pools_mutex:
            if key not in _pools:
                log.debug("HTTP-GET: Creating pool for key %s", key)
                pool = HTTPConnectionPool(scheme, netloc, size=size)
                _pools[key] = pool
            else:
                pool = _pools[key]

        return pool
