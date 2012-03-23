#!/usr/bin/env python

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

from cStringIO import StringIO
from errno import (EACCES, EBADF, EINVAL, EISDIR, EIO, ENOENT, ENOTDIR,
                    ENOTEMPTY)
from getpass import getuser
from stat import S_IFDIR, S_IFREG
from sys import argv
from time import time

from synnefo.lib.parsedate import parse_http_date

from pithos.tools.lib.client import OOS_Client, Fault
from pithos.tools.lib.fuse import FUSE, FuseOSError, Operations
from pithos.tools.lib.util import get_user, get_auth, get_url


epoch = int(time())


class StoreFS(Operations):
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.client = OOS_Client(get_url(), get_auth(), get_user())
    
    def __call__(self, op, path, *args):
        container, sep, object = path[1:].partition('/')
        if self.verbose:
            data = repr(args)[:100]
            print '-> %s %r %r %r' % (op, container, object, data)
        ret = '[Unhandled Exception]'
        
        try:
            if object:
                func = getattr(self, 'object_' + op, None)
                funcargs = (container, object) + args
            elif container:
                func = getattr(self, 'container_' + op, None)
                funcargs = (container,) + args
            else:
                func = getattr(self, 'account_' + op, None)
                funcargs = args

            if not func:
                # Fallback to defaults
                func = getattr(self, op)
                funcargs = (path,) + args
            
            ret = func(*funcargs)
            return ret
        except FuseOSError, e:
            ret = str(e)
            raise
        finally:
            if self.verbose:
                print '<-', op, repr(ret)
    
    
    def _get_container_meta(self, container, **kwargs):
        try:
            return self.client.retrieve_container_metadata(container, **kwargs)
        except Fault:
            raise FuseOSError(ENOENT)
    
    def _get_object_meta(self, container, object, **kwargs):
        try:
            return self.client.retrieve_object_metadata(container, object,
                                                        **kwargs)
        except Fault:
            raise FuseOSError(ENOENT)
    
    
    # Global
    
    def statfs(self, path):
        return dict(f_bsize=1024, f_blocks=1024**2, f_bfree=1024**2,
                    f_bavail=1024**2)
    
    
    # Account Level
    
    def account_chmod(self, mode):
        self.client.update_account_metadata(mode=str(mode))
    
    def account_chown(self, uid, gid):
        self.client.update_account_metadata(uid=uid, gid=gid)
    
    def account_getattr(self, fh=None):
        meta = self.client.retrieve_account_metadata()
        mode = int(meta.get('x-account-meta-mode', 0755))
        last_modified = meta.get('last-modified', None)
        modified = parse_http_date(last_modified) if last_modified else epoch
        count = int(meta['x-account-container-count'])
        uid = int(meta.get('x-account-meta-uid', 0))
        gid = int(meta.get('x-account-meta-gid', 0))
        
        return {
            'st_mode': S_IFDIR | mode,
            'st_nlink': 2 + count,
            'st_uid': uid,
            'st_gid': gid,
            'st_ctime': epoch,
            'st_mtime': modified,
            'st_atime': modified}
    
    def account_getxattr(self, name, position=0):
        meta = self.client.retrieve_account_metadata(restricted=True)
        return meta.get('xattr-' + name, '')
    
    def account_listxattr(self):
        meta = self.client.retrieve_account_metadata(restricted=True)
        prefix = 'xattr-'
        return [k[len(prefix):] for k in meta if k.startswith(prefix)]
    
    def account_readdir(self, fh):
        return ['.', '..'] + self.client.list_containers() or []
    
    def account_removexattr(self, name):
        attr = 'xattr-' + name
        self.client.delete_account_metadata([attr])
    
    def account_setxattr(self, name, value, options, position=0):
        attr = 'xattr-' + name
        meta = {attr: value}
        self.client.update_account_metadata(**meta)
    
    
    # Container Level
    
    def container_chmod(self, container, mode):
        self.client.update_container_metadata(container, mode=str(mode))
    
    def container_chown(self, container, uid, gid):
        self.client.update_container_metadata(container, uid=uid, gid=gid)
    
    def container_getattr(self, container, fh=None):
        meta = self._get_container_meta(container)
        mode = int(meta.get('x-container-meta-mode', 0755))
        modified = parse_http_date(meta['last-modified'])
        count = int(meta['x-container-object-count'])
        uid = int(meta.get('x-account-meta-uid', 0))
        gid = int(meta.get('x-account-meta-gid', 0))
        
        return {
            'st_mode': S_IFDIR | mode,
            'st_nlink': 2 + count,
            'st_uid': uid,
            'st_gid': gid,
            'st_ctime': epoch,
            'st_mtime': modified,
            'st_atime': modified}
    
    def container_getxattr(self, container, name, position=0):
        meta = self._get_container_meta(container)
        return meta.get('xattr-' + name, '')
    
    def container_listxattr(self, container):
        meta = self._get_container_meta(container, restricted=True)
        prefix = 'xattr-'
        return [k[len(prefix):] for k in meta if k.startswith(prefix)]
    
    def container_mkdir(self, container, mode):
        mode = str(mode & 0777)
        self.client.create_container(container, mode=mode)
    
    def container_readdir(self, container, fh):
        objects = self.client.list_objects(container, delimiter='/', prefix='')
        files = [o for o in objects if not o.endswith('/')]
        return ['.', '..'] + files
    
    def container_removexattr(self, container, name):
        attr = 'xattr-' + name
        self.client.delete_container_metadata(container, [attr])
    
    def container_rename(self, container, path):
        new_container, sep, new_object = path[1:].partition('/')
        if not new_container or new_object:
            raise FuseOSError(EINVAL)
        self.client.delete_container(container)
        self.client.create_container(new_container)
    
    def container_rmdir(self, container):
        try:
            self.client.delete_container(container)
        except Fault:
            raise FuseOSError(ENOENT)
    
    def container_setxattr(self, container, name, value, options, position=0):
        attr = 'xattr-' + name
        meta = {attr: value}
        self.client.update_container_metadata(container, **meta)
    
    
    # Object Level
    
    def object_chmod(self, container, object, mode):
        self.client.update_object_metadata(container, object, mode=str(mode))
    
    def object_chown(self, container, uid, gid):
        self.client.update_object_metadata(container, object,
                                            uid=str(uid), gid=str(gid))
    
    def object_create(self, container, object, mode, fi=None):
        mode &= 0777
        self.client.create_object(container, object,
                                    f=None,
                                    content_type='application/octet-stream',
                                    mode=str(mode))
        return 0
    
    def object_getattr(self, container, object, fh=None):
        meta = self._get_object_meta(container, object)
        modified = parse_http_date(meta['last-modified'])
        uid = int(meta.get('x-account-meta-uid', 0))
        gid = int(meta.get('x-account-meta-gid', 0))
        size = int(meta.get('content-length', 0))
        
        if meta['content-type'].split(';', 1)[0].strip() == 'application/directory':
            mode = int(meta.get('x-object-meta-mode', 0755))
            flags = S_IFDIR
            nlink = 2
        else:
            mode = int(meta.get('x-object-meta-mode', 0644))
            flags = S_IFREG
            nlink = 1
        
        return {
            'st_mode': flags | mode,
            'st_nlink': nlink,
            'st_uid': uid,
            'st_gid': gid,
            'st_ctime': epoch,
            'st_mtime': modified,
            'st_atime': modified,
            'st_size': size}
    
    def object_getxattr(self, container, object, name, position=0):
        meta = self._get_object_meta(container, object, restricted=True)
        return meta.get('xattr-' + name, '')
    
    def object_listxattr(self, container, object):
        meta = self._get_object_meta(container, object, restricted=True)
        prefix = 'xattr-'
        return [k[len(prefix):] for k in meta if k.startswith(prefix)]
    
    def object_mkdir(self, container, object, mode):
        mode = str(mode & 0777)
        self.client.create_directory_marker(container, object)
        self.client.update_object_metadata(container, object, mode=mode)
    
    def object_read(self, container, object, nbyte, offset, fh):
        data = self.client.retrieve_object(container, object)
        return data[offset:offset + nbyte]
    
    def object_readdir(self, container, object, fh):
        objects = self.client.list_objects(container, delimiter='/',
                                            prefix=object)
        files = [o.rpartition('/')[2] for o in objects if not o.endswith('/')]
        return ['.', '..'] + files
    
    def object_removexattr(self, container, object, name):
        attr = 'xattr-' + name
        self.client.delete_object_metadata(container, object, [attr])
    
    def object_rename(self, container, object, path):
        new_container, sep, new_object = path[1:].partition('/')
        if not new_container or not new_object:
            raise FuseOSError(EINVAL)
        self.client.move_object(container, object, new_container, new_object)
    
    def object_rmdir(self, container, object):
        self.client.delete_object(container, object)
    
    def object_setxattr(self, container, object, name, value, options,
                        position=0):
        attr = 'xattr-' + name
        meta = {attr: value}
        self.client.update_object_metadata(container, object, **meta)
    
    def object_truncate(self, container, object, length, fh=None):
        data = self.client.retrieve_object(container, object)
        f = StringIO(data[:length])
        self.client.update_object(container, object, f)
    
    def object_unlink(self, container, object):
        self.client.delete_object(container, object)
    
    def object_write(self, container, object, data, offset, fh):
        f = StringIO(data)
        self.client.update_object(container, object, f, offset=offset)
        return len(data)


def main():
    if len(argv) != 2:
        print 'usage: %s <mountpoint>' % argv[0]
        exit(1)
    
    user = getuser()
    fs = StoreFS(verbose=True)
    fuse = FUSE(fs, argv[1], foreground=True)


if __name__ == '__main__':
    main()

