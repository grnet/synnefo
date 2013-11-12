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

from archipelagoblocker import ArchipelagoBlocker


class Blocker(object):
    """Blocker.
       Required constructor parameters: blocksize, blockpath, hashtype.
       Optional blockpool.
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
