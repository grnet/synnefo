
from synnefo.lib.pool import ObjectPool

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


USAGE_LIMIT = 25
RETRY_LIMIT = 100


def init_http_pooling(size):
    global pool_size
    pool_size = size


def put_http_connection(conn):
    pool = conn._pool
    if pool is None:
        return
    conn._pool = None
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
        conn.close = instancemethod(put_http_connection,
                                    conn, type(conn))
        return conn

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


def _verify_connection(conn):
    try:
        conn.request("HEAD", "/")
        conn.getresponse().read()
    except HTTPException:
        # The connection has died.
        conn.close()
        return False
    return True


def get_http_connection(netloc=None, scheme='http'):
    if netloc is None:
        m = "netloc cannot be None"
        raise ValueError(m)
    # does the pool need to be created?
    if netloc not in _pools:
        pool = HTTPConnectionPool(scheme, netloc, size=pool_size)
        _pools[netloc] = pool

    pool = _pools[netloc]

    conn = None
    n = 0
    while conn is None:
        conn = pool.pool_get()
        conn._pool = pool
        if not _verify_connection(conn):
            # The connection has died, e.g., Keepalive expired
            conn = None
            n += 1
            if n > RETRY_LIMIT:
                m = ("Could not get live HTTP conn from pool"
                     "after %d retries." % RETRY_LIMIT)
                raise RuntimeError(m)
    
    return conn

