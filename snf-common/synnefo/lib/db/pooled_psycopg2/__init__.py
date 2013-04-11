# Copyright 2012 GRNET S.A. All rights reserved.
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
#

import psycopg2
from objpool import ObjectPool

from select import select
import logging
log = logging.getLogger(__name__)


_pool_kwargs = None
_pool = None


# How many times to retry on getting a live connection
# from the pool, before giving up.
RETRY_LIMIT = 1000


class PooledConnection(object):
    """Thin wrapper around a psycopg2 connection for a pooled connection.

    It takes care to put itself back into the pool upon connection closure.

    """
    def __init__(self, pool, conn):
        log.debug("INIT-POOLED: pool = %s, conn = %s", pool, conn)
        self._pool = pool
        self._conn = conn

    def close(self):
        log.debug("CLOSE-POOLED: self._pool = %s", self._pool)
        if not self._pool:
            return

        pool = self._pool
        log.debug("PUT-POOLED-BEFORE: about to return %s to the pool", self)
        pool.pool_put(self)
        log.debug("PUT-POOLED-AFTER: returned %s to the pool", self)

    def __getattr__(self, attr):
        """Proxy every other call to the real connection"""
        return getattr(self._conn, attr)

    def __setattr__(self, attr, val):
        if attr not in ("_pool", "_conn"):
            setattr(self._conn, attr, val)
        object.__setattr__(self, attr, val)


class Psycopg2ConnectionPool(ObjectPool):
    """A objpool.ObjectPool of psycopg2 connections.

    Every connection knows how to return itself to the pool
    when it gets close()d.

    """

    def __init__(self, **kw):
        ObjectPool.__init__(self, size=kw["synnefo_poolsize"])
        kw.pop("synnefo_poolsize")
        self._connection_args = kw

    def _pool_create(self):
        log.info("CREATE: about to get a new connection from psycopg2")
        conn = psycopg2._original_connect(**self._connection_args)
        log.info("CREATED: got connection %s from psycopg2", conn)
        return PooledConnection(self, conn)

    def _pool_verify_execute(pooledconn):
        try:
            cursor = pooledconn.cursor()
            cursor.execute("SELECT 1")
        except psycopg2.Error:
            # The connection has died.
            pooledconn.close()
            return False
        return True

    def _pool_verify(self, conn):
        if select((conn.fileno(),), (), (), 0)[0]:
            return False
        return True

    def _pool_cleanup(self, pooledconn):
        log.debug("CLEANING, conn = %d", id(pooledconn))
        try:
            # Reset this connection before putting it back
            # into the pool
            pooledconn.rollback()
        except psycopg2.Error:
            # Since we're not going to be putting the psycopg2 connection
            # back into the pool, close it uncoditionally.
            log.error("Detected dead connection, conn = %d, %s",
                      id(pooledconn), pooledconn)
            try:
                pooledconn._conn.close()
            except:
                pass
            return True
        return False


def _init_pool(kw):
    global _pool
    global _pool_kwargs

    _pool_kwargs = kw
    _pool = Psycopg2ConnectionPool(**kw)


def _get_pool(kw):
    if not _pool:
        log.debug("INIT-POOL: Initializing DB connection pool")
        _init_pool(kw)

    if _pool_kwargs != kw:
        raise NotImplementedError(("Requested pooled psycopg2 connection with "
                                   "args %s != %s." % (kw, _pool_kwargs)))
    return _pool


def _pooled_connect(**kw):
    poolsize = kw.get("synnefo_poolsize", 0)
    if not poolsize:
        kw.pop("synnefo_poolsize", None)
        return psycopg2._original_connect(**kw)

    pool = _get_pool(kw)
    log.debug("GET-POOL: Pool: %r", pool)
    r = pool.pool_get()
    log.debug("GOT-POOL: Got connection %d from pool %r", id(r), pool)
    return r


def monkey_patch_psycopg2():
    """Monkey-patch psycopg2's connect(), to retrieve connections from a pool.

    To enable pooling, you need to pass a synnefo_poolsize argument
    inside psycopg2's connection options.

    """

    if hasattr(psycopg2, '_original_connect'):
        return

    psycopg2._original_connect = psycopg2.connect
    psycopg2.connect = _pooled_connect
