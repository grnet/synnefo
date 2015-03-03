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

from blocker import Blocker
from mapper import Mapper


class Store(object):
    """Store.
       Required constructor parameters: path, block_size, hash_algorithm,
       blockpool, mappool.
    """

    def __init__(self, **params):
        pb = {'blocksize': params['block_size'],
              'hashtype': params['hash_algorithm'],
              'archipelago_cfile': params['archipelago_cfile'],
              }
        self.blocker = Blocker(**pb)
        pm = {'namelen': self.blocker.hashlen,
              'hashtype': params['hash_algorithm'],
              'archipelago_cfile': params['archipelago_cfile'],
              }
        self.mapper = Mapper(**pm)

    def map_get(self, name, size):
        return self.mapper.map_retr(name, size)

    def map_put(self, name, map, size, block_size):
        self.mapper.map_stor(name, map, size, block_size)

    def map_delete(self, name):
        pass

    def map_copy(self, dst, src, size):
        self.mapper.map_copy(dst, src, size)

    def block_get(self, hash):
        blocks = self.blocker.block_retr((hash,))
        if not blocks:
            return None
        return blocks[0]

    def block_get_archipelago(self, hash):
        blocks = self.blocker.block_retr_archipelago((hash,))
        if not blocks:
            return None
        return blocks[0]

    def block_put(self, data):
        hashes, absent = self.blocker.block_stor((data,))
        return hashes[0]

    def block_update(self, hash, offset, data):
        h, e = self.blocker.block_delta(hash, offset, data)
        return h

    def block_search(self, map):
        return self.blocker.block_ping(map)
