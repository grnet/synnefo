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

import hashlib
import os

from binascii import hexlify

from progress.bar import IncrementalBar


def file_read_iterator(fp, size=1024):
    while True:
        data = fp.read(size)
        if not data:
            break
        yield data


class HashMap(list):

    def __init__(self, blocksize, blockhash):
        super(HashMap, self).__init__()
        self.blocksize = blocksize
        self.blockhash = blockhash

    def _hash_raw(self, v):
        h = hashlib.new(self.blockhash)
        h.update(v)
        return h.digest()

    def _hash_block(self, v):
        return self._hash_raw(v.rstrip('\x00'))

    def hash(self):
        if len(self) == 0:
            return self._hash_raw('')
        if len(self) == 1:
            return self.__getitem__(0)

        h = list(self)
        s = 2
        while s < len(h):
            s = s * 2
        h += [('\x00' * len(h[0]))] * (s - len(h))
        while len(h) > 1:
            h = [self._hash_raw(h[x] + h[x + 1]) for x in range(0, len(h), 2)]
        return h[0]

    def load(self, fp):
        self.size = 0
        file_size = os.fstat(fp.fileno()).st_size
        nblocks = 1 + (file_size - 1) // self.blocksize
        bar = IncrementalBar('Computing', max=nblocks)
        bar.suffix = '%(percent).1f%% - %(eta)ds'
        for block in bar.iter(file_read_iterator(fp, self.blocksize)):
            self.append(self._hash_block(block))
            self.size += len(block)


def merkle(path, blocksize=4194304, blockhash='sha256'):
    hashes = HashMap(blocksize, blockhash)
    hashes.load(open(path))
    return hexlify(hashes.hash())
