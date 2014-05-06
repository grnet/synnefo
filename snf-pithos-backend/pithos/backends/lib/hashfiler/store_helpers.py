# Copyright 2014 GRNET S.A. All rights reserved.
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
from hashlib import new as newhasher


def bootstrap_backend_storage(storageType, **params):
    umask = params['umask']
    path = params['path']
    if umask is not None:
        os.umask(umask)
    if storageType.lower() == 'nfs':
        if path and not os.path.exists(path):
            os.makedirs(path)
        if not os.path.isdir(path):
            raise RuntimeError("Cannot open path '%s'" % (path,))
    elif storageType.lower() == 'rados':
        import rados
        cluster = rados.Rados(conffile=params['rados_ceph_conf'])
        cluster.connect()
        if not cluster.pool_exists(params['blockpool']):
            try:
                cluster.create_pool(paramas['blockpool'])
            except Exception as err:
                err_msg = "Cannot create %s RADOS Pool"
                raise RuntimeError(err_msg % params['blockpool'])
        if not cluster.pool_exists(params['mappool']):
            try:
                cluster.create_pool(params['mappool'])
            except Exception as err:
                err_msg = "Cannot create %s RADOS Pool"
                raise RuntimeError(err_msg % params['mappool'])
        cluster.shutdown()
    else:
        raise RuntimeError("Wrong Pithos+ backend storage, '%s'" % storageType)
    hashtype = params['hash_algorithm']
    try:
        hasher = newhasher(hashtype)
    except ValueError:
        msg = "Variable hashtype '%s' is not available from hashlib"
        raise ValueError(msg % (hashtype,))

    hasher.update("")
    emptyhash = hasher.digest()

    pb = {'blocksize': params['block_size'],
          'blockpath': os.path.join(path + '/blocks'),
          'hashtype': params['hash_algorithm'],
          'blockpool': params['blockpool'],
          'backend_storage': params['backend_storage'],
          'rados_ceph_conf': params['rados_ceph_conf']}
    pm = {'mappath': os.path.join(path + '/maps'),
          'namelen': len(emptyhash),
          'mappool': params['mappool'],
          'backend_storage': params['backend_storage'],
          'rados_ceph_conf': params['rados_ceph_conf']}

    return (pb, pm)


def get_blocker(storageType, **params):
    rblocker = None
    fblocker = None
    hashlen = None
    blocksize = None
    if storageType.lower() == 'rados':
        if params['blockpool']:
            from radosblocker import RadosBlocker
            rblocker = RadosBlocker(**params)
            hashlen = rblocker.hashlen
            blocksize = params['blocksize']
        else:
            raise RuntimeError("Undefined RADOS block pool")
    elif storageType.lower() == 'nfs':
        from fileblocker import FileBlocker
        fblocker = FileBlocker(**params)
        hashlen = fblocker.hashlen
        blocksize = params['blocksize']
    else:
        raise RuntimeError("Wrong Pithos+ backend storage, '%s'" % storageType)
    return (fblocker, rblocker, hashlen, blocksize)


def get_mapper(storageType, **params):
    rmap = None
    fmap = None
    if storageType.lower() == 'rados':
        if params['mappool']:
            from radosmapper import RadosMapper
            rmap = RadosMapper(**params)
        else:
            raise RuntimeError("Undefined RADOS map pool")
    elif storageType.lower() == 'nfs':
        from filemapper import FileMapper
        fmap = FileMapper(**params)
    else:
        raise RuntimeError("Wrong Pithos+ backend storage, '%s'" % storageType)
    return (fmap, rmap)
