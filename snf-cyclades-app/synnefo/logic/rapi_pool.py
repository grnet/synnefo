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

from objpool import ObjectPool
from synnefo.logic.rapi import GanetiRapiClient

from logging import getLogger
log = getLogger(__name__)

_pools = {}
_hashes = {}
pool_size = 8


class GanetiRapiClientPool(ObjectPool):
    """Pool of Ganeti RAPI Clients."""

    def __init__(self, host, port, user, passwd, size=None):
        log.debug("INIT: Initializing pool of size %d, host %s,"
                  " port %d, user %s", size, host, port, user)
        ObjectPool.__init__(self, size=size)
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd

    def _pool_create(self):
        log.debug("CREATE: Creating new client from pool %r", self)
        client = GanetiRapiClient(self.host, self.port, self.user, self.passwd)
        client._pool = self
        return client

    def _pool_verify(self, client):
        return True

    def _pool_cleanup(self, conn):
        return False


def get_rapi_client(backend_id, backend_hash, host, port, user, passwd):
    """Get a ganeti RAPI client from pool."""
    log.debug("GET: Getting RAPI client")
    m = "%s cannot be None"
    if host is None:
        raise ValueError(m % "host")
    if port is None:
        raise ValueError(m % "port")

    # does the pool need to be created?
    if backend_hash not in _pools:
        log.debug("GET: No Pool. Creating new for host %s", host)
        pool = GanetiRapiClientPool(host, port, user, passwd, pool_size)
        _pools[backend_hash] = pool
        # Delete Pool for old backend_hash
        if backend_id in _hashes:
            del _pools[_hashes[backend_id]]
        _hashes[backend_id] = backend_hash

    obj = _pools[backend_hash].pool_get()
    log.debug("GET: Got object %r from pool", obj)
    return obj


def put_rapi_client(client):
    pool = client._pool
    log.debug("PUT: putting client %r back to pool %r", client, pool)
    if pool is None:
        log.debug("PUT: client %r does not have a pool", client)
        return
    pool.pool_put(client)
