#!/usr/bin/env python

from django.core.management import setup_environ
from pithos import settings
setup_environ(settings)

from functools import partial
from getpass import getuser
from errno import EACCES, EBADF, EINVAL, EISDIR, ENOENT, ENOTDIR, ENOTEMPTY
from stat import S_IFDIR, S_IFREG
from sys import argv
from time import time

from pithos.api.util import hashmap_hash
from pithos.backends import backend
from pithos.lib.fuse import FUSE, FuseOSError, Operations, LoggingMixIn


epoch = int(time())


class BackendProxy(object):
    """A proxy object that always passes user and account as first args."""
    
    def __init__(self, backend, user, account):
        self.backend = backend
        self.user = user
        self.account = account
    
    def __getattr__(self, name):
        func = getattr(self.backend, name)
        return partial(func, self.user, self.account)


def blocksplit(data, blocksize):
    """An iterator that splits data into blocks of size `blocksize`."""
    
    while data:
        yield data[:blocksize]
        data = data[blocksize:]


class BackendFS(LoggingMixIn, Operations):
    def __init__(self, account):
        self.user = None
        self.account = account
        self.backend = BackendProxy(backend, self.user, self.account)
    
    def create(self, path, mode, fi=None):
        container, sep, object = path[1:].partition('/')
        if not object:
            raise FuseOSError(EACCES)
        
        hashmap = []
        meta = {'hash': hashmap_hash(hashmap)}
        self.backend.update_object_hashmap(container, object, 0, hashmap,
                                            meta, True)
        return 0
    
    def getattr(self, path, fh=None):
        container, sep, object = path[1:].partition('/')
        if not container:
            # Root level
            containers = self.backend.list_containers()
            return {
                'st_mode': (S_IFDIR | 0755),
                'st_ctime': epoch,
                'st_mtime': epoch,
                'st_atime': epoch,
                'st_nlink': 2 + len(containers)}
        elif not object:
            # Container level
            try:
                meta = self.backend.get_container_meta(container)
            except NameError:
                raise FuseOSError(ENOENT)
            
            return {
                'st_mode': (S_IFDIR | 0755),
                'st_ctime': epoch,
                'st_mtime': meta['modified'],
                'st_atime': meta['modified'],
                'st_nlink': 2 + meta['count']}
        else:
            # Object level
            try:
                meta = self.backend.get_object_meta(container, object)
            except NameError:
                raise FuseOSError(ENOENT)
            
            return {
                'st_mode': (S_IFREG | 0644),
                'st_ctime': epoch,
                'st_mtime': meta['modified'],
                'st_atime': meta['modified'],
                'st_nlink': 1,
                'st_size': meta['bytes']}
    
    def mkdir(self, path, mode):
        container, sep, object = path[1:].partition('/')
        if object:
            raise FuseOSError(EACCES)
        backend.put_container(self.user, self.account, container)
    
    def read(self, path, nbyte, offset, fh):
        container, sep, object = path[1:].partition('/')
        if not object:
            raise FuseOSError(EBADF)
        
        # XXX This implementation is inefficient,
        # it always reads all the blocks
        size, hashmap = self.backend.get_object_hashmap(container, object)
        buf = []
        for hash in hashmap:
            buf.append(backend.get_block(hash))
        data = ''.join(buf)[:size]
        return data[offset:offset + nbyte]
    
    def readdir(self, path, fh):
        container, sep, object = path[1:].partition('/')
        if not container:
            # Root level
            containers = [c[0] for c in self.backend.list_containers()]
            return ['.', '..'] + containers
        else:
            # Container level
            objects = [o[0] for o in self.backend.list_objects(container)]
            return ['.', '..'] + objects
    
    def rmdir(self, path):
        container, sep, object = path[1:].partition('/')
        if object:
            raise FuseOSError(ENOTDIR)
        
        try:
            self.backend.delete_container(container)
        except NameError:
            raise FuseOSError(ENOENT)
        except IndexError:
            raise FuseOSError(ENOTEMPTY)
    
    def truncate(self, path, length, fh=None):
        container, sep, object = path[1:].partition('/')
        if object:
            raise FuseOSError(EISDIR)
        
        size, hashmap = self.backend.get_object_hashmap(container, object)
        if length > size:
            raise FuseOSError(EINVAL)   # Extension not supported
        
        div, mod = divmod(size, backend.block_size)
        nblocks = div + 1 if mod else div
        meta = {'hash': hashmap_hash(hashmap)}
        self.backend.update_object_hashmap(container, object, size,
                                            hashmap[:nblocks], meta, True)
    
    def unlink(self, path):
        container, sep, object = path[1:].partition('/')
        if not object:
            raise FuseOSError(EACCES)
        self.backend.delete_object(container, object)
    
    def write(self, path, data, offset, fh):
        container, sep, object = path[1:].partition('/')
        if not object:
            raise FuseOSError(EBADF)
        
        hashmap = []
        for block in blocksplit(data, backend.block_size):
            hashmap.append(backend.put_block(block))
        meta = {'hash': hashmap_hash(hashmap)}
        self.backend.update_object_hashmap(container, object, len(data),
                                            hashmap, meta, True)
        return len(data)


if __name__ == "__main__":
    if len(argv) != 2:
        print 'usage: %s <mountpoint>' % argv[0]
        exit(1)
    account = getuser()
    fuse = FUSE(BackendFS(account), argv[1], foreground=True)
