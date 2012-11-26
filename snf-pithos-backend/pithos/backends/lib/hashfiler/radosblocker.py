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

from hashlib import new as newhasher
from binascii import hexlify
from rados import *

from context_object import RadosObject, file_sync_read_chunks

CEPH_CONF_FILE="/etc/ceph/ceph.conf"

class RadosBlocker(object):
    """Blocker.
       Required constructor parameters: blocksize, blockpath, hashtype.
    """

    blocksize = None
    blockpool = None
    hashtype = None

    def __init__(self, **params):
        blocksize = params['blocksize']
        blockpool = params['blockpool']

        rados = Rados(conffile=CEPH_CONF_FILE)
        rados.connect()
        if not rados.pool_exists(blockpool):
            rados.create_pool(blockpool)

        ioctx = rados.open_ioctx(blockpool)

        hashtype = params['hashtype']
        try:
            hasher = newhasher(hashtype)
        except ValueError:
            msg = "Variable hashtype '%s' is not available from hashlib"
            raise ValueError(msg % (hashtype,))

        hasher.update("")
        emptyhash = hasher.digest()

        self.blocksize = blocksize
        self.blockpool = blockpool
        self.rados = rados
        self.ioctx = ioctx
        self.hashtype = hashtype
        self.hashlen = len(emptyhash)
        self.emptyhash = emptyhash

    def _pad(self, block):
        return block + ('\x00' * (self.blocksize - len(block)))

    def _get_rear_block(self, blkhash, create=0):
        name = hexlify(blkhash)
        return RadosObject(name, self.ioctx, create)

    def _check_rear_block(self, blkhash):
        filename = hexlify(blkhash)
        try:
            self.ioctx.stat(filename)
            return True
        except ObjectNotFound:
            return False

    def block_hash(self, data):
        """Hash a block of data"""
        hasher = newhasher(self.hashtype)
        hasher.update(data.rstrip('\x00'))
        return hasher.digest()

    def block_ping(self, hashes):
        """Check hashes for existence and
           return those missing from block storage.
        """
        notfound = []
        append = notfound.append

        for h in hashes:
            if h not in notfound and not self._check_rear_block(h):
                append(h)

        return notfound

    def block_retr(self, hashes):
        """Retrieve blocks from storage by their hashes."""
        blocksize = self.blocksize
        blocks = []
        append = blocks.append
        block = None

        for h in hashes:
            if h == self.emptyhash:
                append(self._pad(''))
                continue
            with self._get_rear_block(h, 0) as rbl:
                if not rbl:
                    break
                for block in rbl.sync_read_chunks(blocksize, 1, 0):
                    break # there should be just one block there
            if not block:
                break
            append(self._pad(block))

        return blocks

    def block_stor(self, blocklist):
        """Store a bunch of blocks and return (hashes, missing).
           Hashes is a list of the hashes of the blocks,
           missing is a list of indices in that list indicating
           which blocks were missing from the store.
        """
        block_hash = self.block_hash
        hashlist = [block_hash(b) for b in blocklist]
        mf = None
        missing = [i for i, h in enumerate(hashlist) if not self._check_rear_block(h)]
        for i in missing:
            with self._get_rear_block(hashlist[i], 1) as rbl:
                 rbl.sync_write(blocklist[i]) #XXX: verify?

        return hashlist, missing

    def block_delta(self, blkhash, offset, data):
        """Construct and store a new block from a given block
           and a data 'patch' applied at offset. Return:
           (the hash of the new block, if the block already existed)
        """

        blocksize = self.blocksize
        if offset >= blocksize or not data:
            return None, None

        block = self.block_retr((blkhash,))
        if not block:
            return None, None

        block = block[0]
        newblock = block[:offset] + data
        if len(newblock) > blocksize:
            newblock = newblock[:blocksize]
        elif len(newblock) < blocksize:
            newblock += block[len(newblock):]

        h, a = self.block_stor((newblock,))
        return h[0], 1 if a else 0

    def block_hash_file(self, radosobject):
        """Return the list of hashes (hashes map)
           for the blocks in a buffered file.
           Helper method, does not affect store.
        """
        hashes = []
        append = hashes.append
        block_hash = self.block_hash

        for block in file_sync_read_chunks(radosobject, self.blocksize, 1, 0):
            append(block_hash(block))

        return hashes

    def block_stor_file(self, radosobject):
        """Read blocks from buffered file object and store them. Return:
           (bytes read, list of hashes, list of hashes that were missing)
        """
        blocksize = self.blocksize
        block_stor = self.block_stor
        hashlist = []
        hextend = hashlist.extend
        storedlist = []
        sextend = storedlist.extend
        lastsize = 0

        for block in file_sync_read_chunks(radosobject, blocksize, 1, 0):
            hl, sl = block_stor((block,))
            hextend(hl)
            sextend(sl)
            lastsize = len(block)

        size = (len(hashlist) -1) * blocksize + lastsize if hashlist else 0
        return size, hashlist, storedlist

