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

from binascii import hexlify
import os
import re
import ctypes
import ConfigParser
import logging

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

logger = logging.getLogger(__name__)

class ArchipelagoMapper(object):
    """Mapper.
       Required constructor parameters: namelen.
    """

    namelen = None

    def __init__(self, **params):
        self.params = params
        self.namelen = params['namelen']
        cfg = {}
        bcfg = ConfigParser.ConfigParser()
        bcfg.readfp(open(glue.WorkerGlue.ArchipelagoConfFile))
        cfg['blockerm'] = bcfg.getint('mapperd','blockerm_port')
        cfg['mapperd'] = bcfg.getint('vlmcd','mapper_port')
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
                hashes = hashes + (data[idx:idx + namelen],)
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
        req = Request.get_close_request(ioctx, self.mapperd_port, maphash);
        req.submit()
        req.wait()
        ret = req.success();
        if ret is False:
            logger.warning("Could not close map %s" % maphash)
            pass
        req.put();
        self.ioctx_pool.pool_put(ioctx)
        return hashes

    def map_stor(self, maphash, hashes=(), blkoff=0, create=1):
        """Store hashes in the given hashes map."""
        namelen = self.namelen
        if self._check_rear_map(maphash):
            return
        with self._get_rear_map(maphash, 1) as rmap:
            rmap.sync_write_chunks(namelen, blkoff, hashes, None)
