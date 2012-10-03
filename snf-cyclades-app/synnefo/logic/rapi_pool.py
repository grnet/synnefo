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
from synnefo.logic.rapi import GanetiRapiClient

from logging import getLogger
log = getLogger(__name__)

_pools = {}
pool_size = 8


class GanetiRapiClientPool(ObjectPool):
    """Pool of Ganeti RAPI Clients."""

    def __init__(self, host, port, user, passwd, size=None):
        log.debug("INIT: Initializing pool of size %d, host %s," \
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
        # TODO: Delete Pool for old backend_hash

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
