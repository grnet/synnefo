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

from binascii import hexlify
import os
import re
import ctypes

from context_archipelago import ArchipelagoObject
from archipelago.common import (
    Request,
    xseg_reply_info,
    xseg_reply_map,
    xseg_reply_map_scatterlist,
    string_at,
    )

from pithos.workers import (
    glue,
    monkey,
    )

monkey.patch_Request()


class ArchipelagoMapper(object):
    """Mapper.
       Required constructor parameters: namelen.
    """

    namelen = None

    def __init__(self, **params):
        self.params = params
        self.namelen = params['namelen']
        cfg = {}
        bcfg = open(glue.WorkerGlue.ArchipelagoConfFile).read()
        cfg['blockerm'] = re.search('\'blockerm_port\'\s*:\s*\d+',
                                    bcfg).group(0).split(':')[1]
        cfg['mapperd'] = re.search('\'mapper_port\'\s*:\s*\d+',
                                   bcfg).group(0).split(':')[1]
        self.ioctx_pool = glue.WorkerGlue().ioctx_pool
        self.dst_port = int(cfg['blockerm'])
        self.mapperd_port = int(cfg['mapperd'])

    def _get_rear_map(self, maphash, create=0):
        name = hexlify(maphash)
        return ArchipelagoObject(name, self.ioctx_pool, self.dst_port, create)

    def _check_rear_map(self, maphash):
        name = hexlify(maphash)
        ioctx = self.ioctx_pool.pool_get()
        req = Request.get_info_request(ioctx, self.dst_port, name)
        req.submit()
        req.wait()
        ret = req.success()
        req.put()
        self.ioctx_pool.pool_put(ioctx)
        if ret:
            return True
        else:
            return False

    def map_retr(self, maphash, blkoff=0, nr=100000000000000):
        """Return as a list, part of the hashes map of an object
           at the given block offset.
           By default, return the whole hashes map.
        """
        namelen = self.namelen
        hashes = ()
        ioctx = self.ioctx_pool.pool_get()
        req = Request.get_info_request(ioctx, self.dst_port,
                                       hexlify(maphash))
        req.submit()
        req.wait()
        ret = req.success()
        if ret:
            info = req.get_data(_type=xseg_reply_info)
            size = int(info.contents.size)
            req.put()
        else:
            req.put()
            self.ioctx_pool.pool_put(ioctx)
            raise RuntimeError("Hashmap '%s' doesn't exists" %
                               hexlify(maphash))
        req = Request.get_read_request(ioctx, self.dst_port,
                                       hexlify(maphash), size=size)
        req.submit()
        req.wait()
        ret = req.success()
        if ret:
            data = string_at(req.get_data(), size)
            req.put()
            self.ioctx_pool.pool_put(ioctx)
            for idx in xrange(0, len(data), namelen):
                hashes = hashes + (data[idx:idx+namelen],)
            hashes = list(hashes)
        else:
            req.put()
            self.ioctx_pool.pool_put(ioctx)
            raise RuntimeError("Hashmap '%s' doesn't exists" %
                               hexlify(maphash))
        return hashes

    def map_retr_archipelago(self, maphash, size):
        """Retrieve Archipelago mapfile"""
        hashes = []
        ioctx = self.ioctx_pool.pool_get()
        maphash = maphash.split("archip:")[1]
        req = Request.get_mapr_request(ioctx, self.mapperd_port, maphash,
                                       offset=0, size=size)
        req.submit()
        req.wait()
        ret = req.success()
        if ret:
            data = req.get_data(xseg_reply_map)
            Segsarray = xseg_reply_map_scatterlist * data.contents.cnt
            segs = Segsarray.from_address(ctypes.addressof(data.contents.segs))
            hashes = [string_at(segs[idx].target, segs[idx].targetlen)
                    for idx in xrange(len(segs))]
            req.put()
        else:
            req.put()
            self.ioctx_pool.pool_put(ioctx)
            raise Exception("Could not retrieve Archipelago mapfile.")
        self.ioctx_pool.pool_put(ioctx)
        return hashes

    def map_stor(self, maphash, hashes=(), blkoff=0, create=1):
        """Store hashes in the given hashes map."""
        namelen = self.namelen
        if self._check_rear_map(maphash):
            return
        with self._get_rear_map(maphash, 1) as rmap:
            rmap.sync_write_chunks(namelen, blkoff, hashes, None)
