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

import os

from hashmap import HashMap
from binascii import hexlify, unhexlify
from cStringIO import StringIO
from client import Fault


def upload(client, file, container, prefix):
    
    meta = client.retrieve_container_metadata(container)
    blocksize = int(meta['x-container-block-size'])
    blockhash = meta['x-container-block-hash']
    
    size = os.path.getsize(file)
    hashes = HashMap(blocksize, blockhash)
    hashes.load(file)
    map = {'bytes': size, 'hashes': [hexlify(x) for x in hashes]}
    
    object = prefix + os.path.split(file)[-1]
    try:
        client.create_object_by_hashmap(container, object, map)
    except Fault, fault:
        if fault.status != 409:
            raise
    else:
        return
    
    missing = fault.data.split('\n')
    if '' in missing:
        del missing[missing.index(''):]
    
    with open(file) as fp:
        for hash in missing:
            offset = hashes.index(unhexlify(hash)) * blocksize
            fp.seek(offset)
            block = fp.read(blocksize)
            client.create_object(container, '.upload', StringIO(block))
    
    client.create_object_by_hashmap(container, object, map)

def download(client, container, object, file):
    
    meta = client.retrieve_container_metadata(container)
    blocksize = int(meta['x-container-block-size'])
    blockhash = meta['x-container-block-hash']
    
    if os.path.isfile(file):
        size = os.path.getsize(file)
        hashes = HashMap(blocksize, blockhash)
        hashes.load(file)
    else:
        size = 0
        hashes = []
    
    map = client.retrieve_object_hashmap(container, object)
    
    with open(file, 'a') as fp:
        for i, h in enumerate(map):
            if i < len(hashes) and h == hashes[i]:
                continue
            start = i * blocksize
            end = '' if i == len(map) - 1 else (i + 1) * blocksize
            data = client.retrieve_object(container, object, range='bytes=%s-%s' % (start, end))
            fp.seek(start)
            fp.write(data)
