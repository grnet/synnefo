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

from store_helpers import get_blocker


class Blocker(object):
    """Blocker.
       Required constructor parameters: blocksize, blockpath, hashtype.
       Optional blockpool.
    """

    def __init__(self, **params):
        fblocker, rblocker, hashlen, blocksize = get_blocker(**params)
        self.fblocker = fblocker
        self.rblocker = rblocker
        self.hashlen = hashlen
        self.blocksize = blocksize

    def block_hash(self, data):
        """Hash a block of data."""
        if self.fblocker:
            return self.fblocker.block_hash(data)
        elif self.rblocker:
            return self.rblocker.block_hash(data)

    def block_ping(self, hashes):
        """Check hashes for existence and
           return those missing from block storage.

        """
        if self.rblocker:
            return self.rblocker.block_ping(hashes)
        elif self.fblocker:
            return self.fblocker.block_ping(hashes)

    def block_retr(self, hashes):
        """Retrieve blocks from storage by their hashes."""
        if self.rblocker:
            return self.rblocker.block_retr(hashes)
        elif self.fblocker:
            return self.fblocker.block_retr(hashes)

    def block_stor(self, blocklist):
        """Store a bunch of blocks and return (hashes, missing).
           Hashes is a list of the hashes of the blocks,
           missing is a list of indices in that list indicating
           which blocks were missing from the store.

        """
        if self.fblocker:
            (hashes, missing) = self.fblocker.block_stor(blocklist)
        elif self.rblocker:
            (hashes, missing) = self.rblocker.block_stor(blocklist)
        return (hashes, missing)

    def block_delta(self, blkhash, offset, data):
        """Construct and store a new block from a given block
           and a data 'patch' applied at offset. Return:
           (the hash of the new block, if the block already existed)
        """
        blocksize = self.blocksize
        if self.fblocker:
            (bhash, existed) = self.fblocker.block_delta(blkhash, offset, data)
        elif self.rblocker:
            (bhash, existed) = self.rblocker.block_delta(blkhash, offset,
                                                         data)
        if not bhash:
            return None, None
        if self.rblocker and not bhash:
            block = self.rblocker.block_retr((blkhash,))
            if not block:
                return None, None
            block = block[0]
            newblock = block[:offset] + data
            if len(newblock) > blocksize:
                newblock = newblock[:blocksize]
            elif len(newblock) < blocksize:
                newblock += block[len(newblock):]
            bhash, existed = self.rblocker.block_stor((newblock,))
        elif self.fblocker and not bhash:
            block = self.fblocker.block_retr((blkhash,))
            if not block:
                return None, None
            block = block[0]
            newblock = block[:offset] + data
            if len(newblock) > blocksize:
                newblock = newblock[:blocksize]
            elif len(newblock) < blocksize:
                newblock += block[len(newblock):]
            bhash, existed = self.fblocker.block_stor((newblock,))

        return bhash, 1 if existed else 0
