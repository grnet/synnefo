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

from binascii import hexlify

from context_object import RadosObject, file_sync_read_chunks
from rados import *

CEPH_CONF_FILE="/etc/ceph/ceph.conf"

class RadosMapper(object):
    """Mapper.
       Required constructor parameters: mappath, namelen.
    """

    mappool = None
    namelen = None

    def __init__(self, **params):
        self.params = params
        self.namelen = params['namelen']
        mappool = params['mappool']

        rados = Rados(conffile=CEPH_CONF_FILE)
        rados.connect()
        ioctx = rados.open_ioctx(mappool)

        self.mappool = mappool
        self.rados = rados
        self.ioctx = ioctx

    def _get_rear_map(self, maphash, create=0):
        name = hexlify(maphash)
        return RadosObject(name, self.ioctx, create)

    def _check_rear_map(self, maphash):
        name = hexlify(maphash)
        try:
            self.ioctx.stat(name)
            return True
        except ObjectNotFound:
            return False

    def map_retr(self, maphash, blkoff=0, nr=100000000000000):
        """Return as a list, part of the hashes map of an object
           at the given block offset.
           By default, return the whole hashes map.
        """
        namelen = self.namelen
        hashes = ()

        with self._get_rear_map(maphash, 0) as rmap:
            if rmap:
                hashes = list(rmap.sync_read_chunks(namelen, nr, blkoff))
        return hashes

    def map_stor(self, maphash, hashes=(), blkoff=0, create=1):
        """Store hashes in the given hashes map."""
        namelen = self.namelen
        if self._check_rear_map(maphash):
            return
        with self._get_rear_map(maphash, 1) as rmap:
            rmap.sync_write_chunks(namelen, blkoff, hashes, None)

