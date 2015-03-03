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

from hashlib import new as newhasher
from binascii import hexlify

import ctypes
import ConfigParser
import logging

from archipelago.common import (
    Request,
    xseg_reply_map,
    xseg_reply_map_scatterlist,
    string_at,
    XF_ASSUMEV0,
    XF_MAPFLAG_READONLY,
    XF_MAPFLAG_ZERO,
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
    hashtype = None
    hashlen = None
    emptyhash = None

    def __init__(self, **params):
        self.params = params
        self.namelen = params['namelen']
        cfg = ConfigParser.ConfigParser()
        cfg.readfp(open(params['archipelago_cfile']))
        self.ioctx_pool = glue.WorkerGlue.ioctx_pool
        self.dst_port = int(cfg.getint('mapperd', 'blockerm_port'))
        self.mapperd_port = int(cfg.getint('vlmcd', 'mapper_port'))

        hashtype = params['hashtype']
        try:
            hasher = newhasher(hashtype)
        except ValueError:
            msg = "Variable hashtype '%s' is not available from hashlib"
            raise ValueError(msg % (hashtype,))

        hasher.update("")
        emptyhash = hasher.digest()

        self.hashtype = hashtype
        self.hashlen = len(emptyhash)
        self.emptyhash = emptyhash

    def map_retr(self, maphash, size):
        """Return as a list, part of the hashes map of an object
           at the given block offset.
           By default, return the whole hashes map.
        """
        archip_emptyhash = hexlify(self.emptyhash)
        hashes = []
        ioctx = self.ioctx_pool.pool_get()
        req = Request.get_mapr_request(ioctx, self.mapperd_port,
                                       maphash, offset=0, size=size)
        flags = req.get_flags()
        flags |= XF_ASSUMEV0
        req.set_flags(flags)
        req.set_v0_size(size)
        req.submit()
        req.wait()
        ret = req.success()
        if ret:
            data = req.get_data(xseg_reply_map)
            Segsarray = xseg_reply_map_scatterlist * data.contents.cnt
            segs = Segsarray.from_address(ctypes.addressof(data.contents.segs))
            for idx in xrange(len(segs)):
                if segs[idx].flags & XF_MAPFLAG_ZERO:
                    hashes.append(archip_emptyhash)
                else:
                    hashes.append(string_at(segs[idx].target,
                                  segs[idx].targetlen))
            req.put()
        else:
            req.put()
            self.ioctx_pool.pool_put(ioctx)
            raise Exception("Could not retrieve Archipelago mapfile.")
        req = Request.get_close_request(ioctx, self.mapperd_port,
                                        maphash)
        req.submit()
        req.wait()
        ret = req.success()
        if ret is False:
            logger.warning("Could not close map %s" % maphash)
            pass
        req.put()
        self.ioctx_pool.pool_put(ioctx)
        return hashes

    def map_stor(self, maphash, hashes, size, block_size):
        """Store hashes in the given hashes map."""
        objects = list()
        archip_emptyhash = hexlify(self.emptyhash)
        for h in hashes:
            if h == archip_emptyhash:
                objects.append({'name': '', 'flags': XF_MAPFLAG_ZERO})
            else:
                objects.append({'name': h, 'flags': XF_MAPFLAG_READONLY})
        ioctx = self.ioctx_pool.pool_get()
        req = Request.get_create_request(ioctx, self.mapperd_port,
                                         maphash,
                                         mapflags=XF_MAPFLAG_READONLY,
                                         objects=objects, blocksize=block_size,
                                         size=size)
        req.submit()
        req.wait()
        ret = req.success()
        if ret is False:
            req.put()
            self.ioctx_pool.pool_put(ioctx)
            raise IOError("Could not write map %s" % maphash)
        req.put()
        self.ioctx_pool.pool_put(ioctx)

    def map_copy(self, dst, src, size):
        """Copies src map into dst."""
        ioctx = self.ioctx_pool.pool_get()
        req = Request.get_copy_request(ioctx, self.mapperd_port,
                                       src, dst, size=size)

        flags = req.get_flags()
        flags |= XF_ASSUMEV0
        req.set_flags(flags)
        req.set_v0_size(size)

        req.submit()
        req.wait()
        ret = req.success()
        if ret is False:
            req.put()
            self.ioctx_pool.pool_put(ioctx)
            raise IOError("Could not copy map %s to %s" % (src, dst))
        req.put()
        self.ioctx_pool.pool_put(ioctx)
