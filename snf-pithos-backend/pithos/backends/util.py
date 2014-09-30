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
    def __init__(self, size=None, **kwargs):
        super(PithosBackendPool, self).__init__(size=size)
        self.backend_kwargs = kwargs

    def _pool_create(self):
        backend = connect_backend(**self.backend_kwargs)
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
