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

from os import SEEK_CUR, SEEK_SET, fsync
from errno import ENOENT, EROFS


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


def file_sync_write_chunks(openfile, chunksize, offset, chunks, size=None):
    """Write given chunks to the given buffered file object.
       Writes never span across chunk boundaries.
       If size is given stop after or pad until size bytes have been written.
    """
    fwrite = openfile.write
    seek = openfile.seek
    padding = 0

    try:
        seek(offset * chunksize)
    except IOError, e:
        seek = None
        for x in xrange(offset):
            fwrite(zeros(chunksize))

    cursize = offset * chunksize

    for chunk in chunks:
        if padding:
            if seek:
                seek(padding - 1, SEEK_CUR)
                fwrite("\x00")
            else:
                fwrite(buffer(zeros(chunksize), 0, padding))
        if size is not None and cursize + chunksize >= size:
            chunk = chunk[:chunksize - (cursize - size)]
            fwrite(chunk)
            cursize += len(chunk)
            break
        fwrite(chunk)
        padding = chunksize - len(chunk)

    padding = size - cursize if size is not None else 0
    if padding <= 0:
        return

    q, r = divmod(padding, chunksize)
    for x in xrange(q):
        fwrite(zeros(chunksize))
    fwrite(buffer(zeros(chunksize), 0, r))


def file_sync_read_chunks(openfile, chunksize, nr, offset=0):
    """Read and yield groups of chunks from a buffered file object at offset.
       Reads never span accros chunksize boundaries.
    """
    fread = openfile.read
    remains = offset * chunksize
    seek = openfile.seek
    try:
        seek(remains)
    except IOError, e:
        seek = None
        while 1:
            s = fread(remains)
            remains -= len(s)
            if remains <= 0:
                break

    while nr:
        remains = chunksize
        chunk = ''
        while 1:
            s = fread(remains)
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


class ContextFile(object):
    __slots__ = ("name", "fdesc", "create")

    def __init__(self, name, create=0):
        self.name = name
        self.fdesc = None
        self.create = create
        #self.dirty = 0

    def __enter__(self):
        name = self.name
        try:
            fdesc = open(name, 'rb+')
        except IOError, e:
            if self.create and e.errno == ENOENT:
                fdesc = open(name, 'w+')
            elif not self.create and e.errno == EROFS:
                fdesc = open(name, 'rb')
            else:
                raise

        self.fdesc = fdesc
        return self

    def __exit__(self, exc, arg, trace):
        fdesc = self.fdesc
        if fdesc is not None:
            #if self.dirty:
            #    fsync(fdesc.fileno())
            fdesc.close()
        return False  # propagate exceptions

    def seek(self, offset, whence=SEEK_SET):
        return self.fdesc.seek(offset, whence)

    def tell(self):
        return self.fdesc.tell()

    def truncate(self, size):
        self.fdesc.truncate(size)

    def sync_write(self, data):
        #self.dirty = 1
        self.fdesc.write(data)

    def sync_write_chunks(self, chunksize, offset, chunks, size=None):
        #self.dirty = 1
        return file_sync_write_chunks(self.fdesc, chunksize, offset, chunks, size)

    def sync_read(self, size):
        read = self.fdesc.read
        data = ''
        while 1:
            s = read(size)
            if not s:
                break
            data += s
        return data

    def sync_read_chunks(self, chunksize, nr, offset=0):
        return file_sync_read_chunks(self.fdesc, chunksize, nr, offset)
