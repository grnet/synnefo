# Copyright (C) 2010-2016 GRNET S.A. and individual contributors
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

from archipelagoblocker import ArchipelagoBlocker


class Blocker(object):
    """Blocker.
       Required constructor parameters: blocksize, blockpath, hashtype.
    """

    def __init__(self, **params):
        self.archip_blocker = ArchipelagoBlocker(**params)
        self.hashlen = self.archip_blocker.hashlen
        self.blocksize = params['blocksize']

    def block_hash(self, data):
        """Hash a block of data"""
        return self.archip_blocker.block_hash(data)

    def block_ping(self, hashes):
        """Check hashes for existence and
           return those missing from block storage.

        """
        return self.archip_blocker.block_ping(hashes)

    def block_retr(self, hashes):
        """Retrieve blocks from storage by their hashes."""
        return self.archip_blocker.block_retr(hashes)

    def block_retr_archipelago(self, hashes):
        """Retrieve blocks from storage by theri hashes."""
        return self.archip_blocker.block_retr_archipelago(hashes)

    def block_stor(self, blocklist):
        """Store a bunch of blocks and return (hashes, missing).
           Hashes is a list of the hashes of the blocks,
           missing is a list of indices in that list indicating
           which blocks were missing from the store.

        """

        (hashes, missing) = self.archip_blocker.block_stor(blocklist)
        return (hashes, missing)

    def block_delta(self, blkhash, offset, data):
        """Construct and store a new block from a given block
           and a data 'patch' applied at offset. Return:
           (the hash of the new block, if the block already existed)
        """
        blocksize = self.blocksize
        archip_hash = None
        archip_existed = True
        (archip_hash, archip_existed) = \
            self.archip_blocker.block_delta(blkhash, offset, data)

        if not archip_hash:
            return None, None

        if self.archip_blocker and not archip_hash:
            block = self.archip_blocker.block_retr((blkhash,))
            if not block:
                return None, None
            block = block[0]
            newblock = block[:offset] + data
            if len(newblock) > blocksize:
                newblock = newblock[:blocksize]
            elif len(newblock) < blocksize:
                newblock += block[len(newblock):]
            archip_hash, archip_existed = self.rblocker.block_stor((newblock,))

        return archip_hash, 1 if archip_existed else 0
