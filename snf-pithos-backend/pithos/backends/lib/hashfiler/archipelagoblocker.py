# Copyright 2013 GRNET S.A. All rights reserved.
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
import os
import re

from context_archipelago import ArchipelagoObject, file_sync_read_chunks
from archipelago.common import (
    Request,
    xseg_reply_info,
    string_at,
    )

from pithos.workers import (
    glue,
    monkey,
    )

monkey.patch_Request()


class ArchipelagoBlocker(object):
    """Blocker.
       Required constructor parameters: blocksize, hashtype.
    """

    blocksize = None
    blockpool = None
    hashtype = None

    def __init__(self, **params):
        cfg = {}
        bcfg = open(glue.WorkerGlue.ArchipelagoConfFile).read()
        cfg['blockerb'] = re.search('\'blockerb_port\'\s*:\s*\d+',
                                    bcfg).group(0).split(':')[1]
        blocksize = params['blocksize']
        hashtype = params['hashtype']
        try:
            hasher = newhasher(hashtype)
        except ValueError:
            msg = "Variable hashtype '%s' is not available from hashlib"
            raise ValueError(msg % (hashtype,))

        hasher.update("")
        emptyhash = hasher.digest()

        self.blocksize = blocksize
        self.ioctx_pool = glue.WorkerGlue().ioctx_pool
        self.dst_port = int(cfg['blockerb'])
        self.hashtype = hashtype
        self.hashlen = len(emptyhash)
        self.emptyhash = emptyhash

    def _pad(self, block):
        return block + ('\x00' * (self.blocksize - len(block)))

    def _get_rear_block(self, blkhash, create=0):
        name = hexlify(blkhash)
        return ArchipelagoObject(name, self.ioctx_pool, self.dst_port, create)

    def _check_rear_block(self, blkhash):
        filename = hexlify(blkhash)
        ioctx = self.ioctx_pool.pool_get()
        req = Request.get_info_request(ioctx, self.dst_port, filename)
        req.submit()
        req.wait()
        ret = req.success()
        req.put()
        self.ioctx_pool.pool_put(ioctx)
        if ret:
            return True
        else:
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
                    break  # there should be just one block there
            if not block:
                break
            append(self._pad(block))

        return blocks

    def block_retr_archipelago(self, hashes):
        """Retrieve blocks from storage by their hashes"""
        blocks = []
        append = blocks.append
        block = None

        ioctx = self.ioctx_pool.pool_get()
        archip_emptyhash = hexlify(self.emptyhash)

        for h in hashes:
            if h == archip_emptyhash:
                append(self._pad(''))
                continue
            req = Request.get_info_request(ioctx, self.dst_port, h)
            req.submit()
            req.wait()
            ret = req.success()
            if ret:
                info = req.get_data(_type=xseg_reply_info)
                size = info.contents.size
                req.put()
                req_data = Request.get_read_request(ioctx, self.dst_port, h,
                                                    size=size)
                req_data.submit()
                req_data.wait()
                ret_data = req_data.success()
                if ret_data:
                    append(self._pad(string_at(req_data.get_data(), size)))
                    req_data.put()
                else:
                    req_data.put()
                    self.ioctx_pool.put(ioctx)
                    raise Exception("Cannot retrieve Archipelago data.")
            else:
                req.put()
                self.ioctx_pool.pool_put(ioctx)
                raise Exception("Bad block file.")
        self.ioctx_pool.pool_put(ioctx)
        return blocks

    def block_stor(self, blocklist):
        """Store a bunch of blocks and return (hashes, missing).
           Hashes is a list of the hashes of the blocks,
           missing is a list of indices in that list indicating
           which blocks were missing from the store.
        """
        block_hash = self.block_hash
        hashlist = [block_hash(b) for b in blocklist]
        missing = [i for i, h in enumerate(hashlist) if not
                   self._check_rear_block(h)]
        for i in missing:
            with self._get_rear_block(hashlist[i], 1) as rbl:
                rbl.sync_write(blocklist[i])  # XXX: verify?

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

    def block_hash_file(self, archipelagoobject):
        """Return the list of hashes (hashes map)
           for the blocks in a buffered file.
           Helper method, does not affect store.
        """
        hashes = []
        append = hashes.append
        block_hash = self.block_hash

        for block in file_sync_read_chunks(archipelagoobject,
                                           self.blocksize, 1, 0):
            append(block_hash(block))

        return hashes

    def block_stor_file(self, archipelagoobject):
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

        for block in file_sync_read_chunks(archipelagoobject, blocksize, 1, 0):
            hl, sl = block_stor((block,))
            hextend(hl)
            sextend(sl)
            lastsize = len(block)

        size = (len(hashlist) - 1) * blocksize + lastsize if hashlist else 0
        return size, hashlist, storedlist
