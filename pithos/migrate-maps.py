#!/usr/bin/env python

import sys
import os
import time
import logging
import hashlib
import binascii

from os import makedirs, unlink
from os.path import isdir, realpath, exists, join
from binascii import hexlify

from backends.lib.hashfiler.context_file import ContextFile

class HashMap(list):
    
    def __init__(self, blocksize, blockhash):
        super(HashMap, self).__init__()
        self.blocksize = blocksize
        self.blockhash = blockhash
    
    def _hash_raw(self, v):
        h = hashlib.new(self.blockhash)
        h.update(v)
        return h.digest()
    
    def hash(self):
        if len(self) == 0:
            return self._hash_raw('')
        if len(self) == 1:
            return self.__getitem__(0)
        
        h = list(self)
        s = 2
        while s < len(h):
            s = s * 2
        h += [('\x00' * len(h[0]))] * (s - len(h))
        while len(h) > 1:
            h = [self._hash_raw(h[x] + h[x + 1]) for x in range(0, len(h), 2)]
        return h[0]

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

    def _get_rear_map(self, maphash, create=0):
        filename = hexlify(maphash)
        dir = join(self.mappath, filename[0:2], filename[2:4], filename[4:6])
        if not exists(dir):
            makedirs(dir)
        name = join(dir, filename)
        return ContextFile(name, create)

    def _check_rear_map(self, maphash):
        filename = hexlify(maphash)
        dir = join(self.mappath, filename[0:2], filename[2:4], filename[4:6])
        name = join(dir, filename)
        return exists(name)

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

if __name__ == "__main__":
    map = HashMap(4 * 1024 * 1024, 'sha256')

    namelen = len(map.hash())
    params = {'mappath': os.path.join('data/pithos/maps-new'),
              'namelen': namelen}
    mapper = Mapper(**params)

    files = os.listdir('data/pithos/maps')
    for f in files:
        with ContextFile(os.path.join('data/pithos/maps', f), 0) as rmap:
            hashes = list(rmap.sync_read_chunks(namelen, 100000000000000, 0))
            map[:] = hashes
            hash = map.hash()
            mapper.map_stor(hash, hashes)
            print 'update versions set hash=\'%s\' where serial=%s;' % (hexlify(hash), int(f, 16))

