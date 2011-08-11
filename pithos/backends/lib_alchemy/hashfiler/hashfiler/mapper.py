# Copyright 2011 GRNET S.A. All rights reserved.
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

from os.path import realpath, join, exists, isdir
from os import makedirs, unlink
from errno import ENOENT

from context_file import ContextFile


class Mapper(object):
    """Mapper.
       Required contstructor parameters: mappath, namelen.
    """
    
    mappath = None
    namelen = None

    def __init__(self, **params):
        self.params = params
        self.namelen = params['namelen']
        mappath = realpath(params['mappath'])
        if not isdir(mappath):
            if not exists(mappath):
                makedirs(mappath)
            else:
                raise ValueError("Variable mappath '%s' is not a directory" % (mappath,))
        self.mappath = mappath

    def _get_rear_map(self, name, create=0):
        name = join(self.mappath, hex(int(name)))
        return ContextFile(name, create)

    def _delete_rear_map(self, name):
        name = join(self.mappath, hex(int(name)))
        try:
            unlink(name)
            return 1
        except OSError, e:
            if e.errno != ENOENT:
                raise
        return 0

    def map_retr(self, name, blkoff=0, nr=100000000000000):
        """Return as a list, part of the hashes map of an object
           at the given block offset.
           By default, return the whole hashes map.
        """
        namelen = self.namelen
        hashes = ()

        with self._get_rear_map(name, 0) as rmap:
            if rmap:
                hashes = list(rmap.sync_read_chunks(namelen, nr, blkoff))
        return hashes

    def map_stor(self, name, hashes=(), blkoff=0, create=1):
        """Store hashes in the given hashes map, replacing the old ones."""
        namelen = self.namelen
        with self._get_rear_map(name, 1) as rmap:
            rmap.sync_write_chunks(namelen, blkoff, hashes, None)

#     def map_copy(self, src, dst):
#         """Copy a hashes map to another one, replacing it."""
#         with self._get_rear_map(src, 0) as rmap:
#             if rmap:
#                 rmap.copy_to(dst)

    def map_remv(self, name):
        """Remove a hashes map. Returns true if the map was found and removed."""
        return self._delete_rear_map(name)

