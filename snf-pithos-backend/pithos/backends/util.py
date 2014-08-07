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
from new import instancemethod
from select import select
from traceback import print_exc
from pithos.backends import connect_backend

USAGE_LIMIT = 500


class PithosBackendPool(ObjectPool):
    def __init__(self, size=None, db_module=None, db_connection=None,
                 block_module=None, block_size=None, hash_algorithm=None,
                 queue_module=None, queue_hosts=None,
                 queue_exchange=None, free_versioning=True,
                 astakos_auth_url=None, service_token=None,
                 astakosclient_poolsize=None,
                 block_params=None,
                 public_url_security=None,
                 public_url_alphabet=None,
                 account_quota_policy=None,
                 container_quota_policy=None,
                 container_versioning_policy=None,
                 archipelago_conf_file=None,
                 xseg_pool_size=8,
                 map_check_interval=None,
                 mapfile_prefix=None):
        super(PithosBackendPool, self).__init__(size=size)
        self.db_module = db_module
        self.db_connection = db_connection
        self.block_module = block_module
        self.block_size = block_size
        self.hash_algorithm = hash_algorithm
        self.queue_module = queue_module
        self.block_params = block_params
        self.queue_hosts = queue_hosts
        self.queue_exchange = queue_exchange
        self.astakos_auth_url = astakos_auth_url
        self.service_token = service_token
        self.astakosclient_poolsize = astakosclient_poolsize
        self.free_versioning = free_versioning
        self.public_url_security = public_url_security
        self.public_url_alphabet = public_url_alphabet
        self.account_quota_policy = account_quota_policy
        self.container_quota_policy = container_quota_policy
        self.container_versioning_policy = container_versioning_policy
        self.archipelago_conf_file = archipelago_conf_file
        self.xseg_pool_size = xseg_pool_size
        self.map_check_interval = map_check_interval
        self.mapfile_prefix = mapfile_prefix

    def _pool_create(self):
        backend = connect_backend(
            db_module=self.db_module,
            db_connection=self.db_connection,
            block_module=self.block_module,
            block_size=self.block_size,
            hash_algorithm=self.hash_algorithm,
            queue_module=self.queue_module,
            block_params=self.block_params,
            queue_hosts=self.queue_hosts,
            queue_exchange=self.queue_exchange,
            astakos_auth_url=self.astakos_auth_url,
            service_token=self.service_token,
            astakosclient_poolsize=self.astakosclient_poolsize,
            free_versioning=self.free_versioning,
            public_url_security=self.public_url_security,
            public_url_alphabet=self.public_url_alphabet,
            account_quota_policy=self.account_quota_policy,
            container_quota_policy=self.container_quota_policy,
            container_versioning_policy=self.container_versioning_policy,
            archipelago_conf_file=self.archipelago_conf_file,
            xseg_pool_size=self.xseg_pool_size,
            map_check_interval=self.map_check_interval,
            mapfile_prefix=self.mapfile_prefix)

        backend._real_close = backend.close
        backend.close = instancemethod(_pooled_backend_close, backend,
                                       type(backend))
        backend._pool = self
        backend._use_count = USAGE_LIMIT
        backend.messages = []
        return backend

    def _pool_verify(self, backend):
        wrapper = backend.wrapper
        conn = wrapper.conn
        if conn.closed:
            return False

        if conn.in_transaction():
            conn.close()
            return False

        try:
            fd = conn.connection.connection.fileno()
        except AttributeError:
            # probably sqlite, assume success
            pass
        else:
            try:
                r, w, x = select([fd], (), (), 0)
                if r:
                    conn.close()
                    return False
            except:
                print_exc()
                return False

        return True

    def _pool_cleanup(self, backend):
        c = backend._use_count - 1
        if c < 0:
            backend._real_close()
            return True

        backend._use_count = c
        wrapper = backend.wrapper
        if wrapper.trans is not None:
            conn = wrapper.conn
            if conn.closed:
                wrapper.trans = None
            else:
                wrapper.rollback()
        backend.messages = []
        return False

    def shutdown(self):
        while True:
            backend = self.pool_get(create=False)
            if backend is None:
                break
            self.pool_put(None)
            backend._real_close()


def _pooled_backend_close(backend):
    backend._pool.pool_put(backend)
