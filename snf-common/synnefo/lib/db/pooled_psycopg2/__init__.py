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

    def _pool_verify(self, conn):
        try:
            # Make sure that the connection is alive before using the fd
            res = conn.poll()
            if res == psycopg2.extensions.POLL_ERROR:
                raise psycopg2.Error

            # There shouldn't be any data available to read. If there is,
            # remove the connection from the pool
            if select((conn.fileno(),), (), (), 0)[0]:
                raise psycopg2.Error
            return True
        except psycopg2.Error:
            # Since we're not going to be putting the psycopg2 connection
            # back into the pool, close it uncoditionally.
            log.info("VERIFY: Detected dead connection")
            try:
                conn.close()
            except:
                pass
            return False

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
        log.debug("INIT-POOL: Requested connection args differ from pool "
                  "args: %s != %s." % (kw, _pool_kwargs))
        raise Exception("Requested pooled psycopg2 connection with args "
                        "that differ from the current pool args")
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
