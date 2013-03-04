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
import types
import json

from hashmap import HashMap
from binascii import hexlify, unhexlify
from cStringIO import StringIO
from client import Fault

from progress.bar import IncrementalBar


def upload(client, path, container, prefix, name=None, mimetype=None):

    meta = client.retrieve_container_metadata(container)
    blocksize = int(meta['x-container-block-size'])
    blockhash = meta['x-container-block-hash']

    size = os.path.getsize(path)
    hashes = HashMap(blocksize, blockhash)
    hashes.load(open(path))
    map = {'bytes': size, 'hashes': [hexlify(x) for x in hashes]}

    objectname = name if name else os.path.split(path)[-1]
    object = prefix + objectname
    kwargs = {'mimetype': mimetype} if mimetype else {}
    v = None
    try:
        v = client.create_object_by_hashmap(container, object, map, **kwargs)
    except Fault, fault:
        if fault.status != 409:
            raise
    else:
        return v

    if isinstance(fault.data, types.StringType):
        missing = json.loads(fault.data)
    elif isinstance(fault.data, types.ListType):
        missing = fault.data

    if '' in missing:
        del missing[missing.index(''):]

    bar = IncrementalBar('Uploading', max=len(missing))
    bar.suffix = '%(percent).1f%% - %(eta)ds'
    with open(path) as fp:
        for hash in missing:
            offset = hashes.index(unhexlify(hash)) * blocksize
            fp.seek(offset)
            block = fp.read(blocksize)
            client.update_container_data(container, StringIO(block))
            bar.next()
    bar.finish()

    return client.create_object_by_hashmap(container, object, map, **kwargs)


def download(client, container, object, path):

    res = client.retrieve_object_hashmap(container, object)
    blocksize = int(res['block_size'])
    blockhash = res['block_hash']
    bytes = res['bytes']
    map = res['hashes']

    if os.path.exists(path):
        h = HashMap(blocksize, blockhash)
        h.load(open(path))
        hashes = [hexlify(x) for x in h]
    else:
        open(path, 'w').close()     # Create an empty file
        hashes = []

    with open(path, 'a+') as fp:
        if bytes != 0:
            for i, h in enumerate(map):
                if i < len(hashes) and h == hashes[i]:
                    continue
                start = i * blocksize
                end = '' if i == len(map) - 1 else ((i + 1) * blocksize) - 1
                data = client.retrieve_object(
                    container, object, range='bytes=%s-%s' % (start, end))
                if i != len(map) - 1:
                    data += (blocksize - len(data)) * '\x00'
                fp.seek(start)
                fp.write(data)
        fp.truncate(bytes)
