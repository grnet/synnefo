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

from synnefo.lib.pool import ObjectPool
from select import select

from httplib import (
        HTTPConnection  as http_class,
        HTTPSConnection as https_class,
        HTTPException,
        ResponseNotReady
)

from urlparse import urlparse
from new import instancemethod


_pools = {}
pool_size = 8


USAGE_LIMIT = 1000


def init_http_pooling(size):
    global pool_size
    pool_size = size


def put_http_connection(conn):
    pool = conn._pool
    if pool is None:
        return
    # conn._pool = None
    pool.pool_put(conn)


class HTTPConnectionPool(ObjectPool):

    _scheme_to_class = {
            'http'  :   http_class,
            'https' :   https_class,
    }

    def __init__(self, scheme, netloc, size=None):
        ObjectPool.__init__(self, size=size)

        connection_class = self._scheme_to_class.get(scheme, None)
        if connection_class is None:
            m = 'Unsupported scheme: %s' % (scheme,)
            raise ValueError(m)

        self.connection_class = connection_class
        self.scheme = scheme
        self.netloc = netloc

    def _pool_create(self):
        conn = self.connection_class(self.netloc)
        conn._use_counter = USAGE_LIMIT
        conn._pool = self
        conn._real_close = conn.close
        conn.close = instancemethod(put_http_connection, conn, type(conn))
        return conn

    def _pool_verify(self, conn):
	if conn is None:
            return False
	sock = conn.sock
        if sock is None:
            return True
        if select((conn.sock,), (), (), 0)[0]:
            return False
        return True

    def _pool_cleanup(self, conn):
        # every connection can be used a finite number of times
        conn._use_counter -= 1

        # see httplib source for connection states documentation
        if conn._use_counter > 0 and conn._HTTPConnection__state == 'Idle':
            try:
                resp = conn.getresponse()
            except ResponseNotReady:
               return False

        conn._real_close()
        return True


def get_http_connection(netloc=None, scheme='http', pool_size=pool_size):
    if netloc is None:
        m = "netloc cannot be None"
        raise ValueError(m)
    # does the pool need to be created?
    if netloc not in _pools:
        pool = HTTPConnectionPool(scheme, netloc, size=pool_size)
        _pools[netloc] = pool

    return _pools[netloc].pool_get()

