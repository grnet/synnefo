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

import os

from blocker import Blocker
from mapper import Mapper

class Store(object):
    """Store.
       Required constructor parameters: path, block_size, hash_algorithm,
       umask, blockpool, mappool.
    """

    def __init__(self, **params):
        umask = params['umask']
        if umask is not None:
            os.umask(umask)

        path = params['path']
        if path and not os.path.exists(path):
            os.makedirs(path)
        if not os.path.isdir(path):
            raise RuntimeError("Cannot open path '%s'" % (path,))

        p = {'blocksize': params['block_size'],
             'blockpath': os.path.join(path + '/blocks'),
             'hashtype': params['hash_algorithm'],
	     'blockpool': params['blockpool']}
        self.blocker = Blocker(**p)
        p = {'mappath': os.path.join(path + '/maps'),
             'namelen': self.blocker.hashlen,
	     'mappool': params['mappool']}
        self.mapper = Mapper(**p)

    def map_get(self, name):
        return self.mapper.map_retr(name)

    def map_put(self, name, map):
        self.mapper.map_stor(name, map)

    def map_delete(self, name):
        pass

    def block_get(self, hash):
        blocks = self.blocker.block_retr((hash,))
        if not blocks:
            return None
        return blocks[0]

    def block_put(self, data):
        hashes, absent = self.blocker.block_stor((data,))
        return hashes[0]

    def block_update(self, hash, offset, data):
        h, e = self.blocker.block_delta(hash, offset, data)
        return h

    def block_search(self, map):
        return self.blocker.block_ping(map)

