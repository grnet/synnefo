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

from os import SEEK_CUR, SEEK_SET
from rados import ObjectNotFound

_zeros = ''


def zeros(nr):
    global _zeros
    size = len(_zeros)
    if nr == size:
        return _zeros

    if nr > size:
        _zeros += '\0' * (nr - size)
        return _zeros

    if nr < size:
        _zeros = _zeros[:nr]
        return _zeros


def file_sync_write_chunks(radosobject, chunksize, offset, chunks, size=None):
    """Write given chunks to the given buffered file object.
       Writes never span across chunk boundaries.
       If size is given stop after or pad until size bytes have been written.
    """
    padding = 0
    cursize = chunksize * offset
    radosobject.seek(cursize)
    for chunk in chunks:
        if padding:
            radosobject.sync_write(buffer(zeros(chunksize), 0, padding))
        if size is not None and cursize + chunksize >= size:
            chunk = chunk[:chunksize - (cursize - size)]
            radosobject.sync_write(chunk)
            cursize += len(chunk)
            break
        radosobject.sync_write(chunk)
        padding = chunksize - len(chunk)

    padding = size - cursize if size is not None else 0
    if padding <= 0:
        return

    q, r = divmod(padding, chunksize)
    for x in xrange(q):
        radosobject.sunc_write(zeros(chunksize))
    radosobject.sync_write(buffer(zeros(chunksize), 0, r))


def file_sync_read_chunks(radosobject, chunksize, nr, offset=0):
    """Read and yield groups of chunks from a buffered file object at offset.
       Reads never span accros chunksize boundaries.
    """
    radosobject.seek(offset * chunksize)
    while nr:
        remains = chunksize
        chunk = ''
        while 1:
            s = radosobject.sync_read(remains)
            if not s:
                if chunk:
                    yield chunk
                return
            chunk += s
            remains -= len(s)
            if remains <= 0:
                break
        yield chunk
        nr -= 1


class RadosObject(object):
    __slots__ = ("name", "ioctx", "create", "offset")

    def __init__(self, name, ioctx, create=0):
        self.name = name
        self.ioctx = ioctx
        self.create = create
        self.offset = 0
        #self.dirty = 0

    def __enter__(self):
        return self

    def __exit__(self, exc, arg, trace):
        return False

    def seek(self, offset, whence=SEEK_SET):
        if whence == SEEK_CUR:
            offset += self.offset
        self.offset = offset
        return offset

    def tell(self):
        return self.offset

    def truncate(self, size):
        self.ioctx.trunc(self.name, size)

    def sync_write(self, data):
        #self.dirty = 1
        self.ioctx.write(self.name, data, self.offset)
        self.offset += len(data)

    def sync_write_chunks(self, chunksize, offset, chunks, size=None):
        #self.dirty = 1
        return file_sync_write_chunks(self, chunksize, offset, chunks, size)

    def sync_read(self, size):
        read = self.ioctx.read
        data = ''
        datalen = 0
        while 1:
            try:
                s = read(self.name, size - datalen, self.offset)
            except ObjectNotFound:
                s = None
            if not s:
                break
            data += s
            datalen += len(s)
            self.offset += len(s)
            if datalen >= size:
                break
        return data

    def sync_read_chunks(self, chunksize, nr, offset=0):
        return file_sync_read_chunks(self, chunksize, nr, offset)
