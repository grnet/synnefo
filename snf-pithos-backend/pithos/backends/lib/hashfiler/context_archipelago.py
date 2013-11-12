# Copyright 2013 GRNET S.A. All rights reserved.
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
from archipelago.common import (
                        Request,
                        string_at,
                    )
from pithos.workers import monkey
monkey.patch_Request()

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


def file_sync_write_chunks(archipelagoobject, chunksize, offset,
                           chunks, size=None):
    """Write given chunks to the given buffered file object.
       Writes never span across chunk boundaries.
       If size is given stop after or pad until size bytes have been written.
    """
    padding = 0
    cursize = chunksize * offset
    archipelagoobject.seek(cursize)
    for chunk in chunks:
        if padding:
            archipelagoobject.sync_write(buffer(zeros(chunksize), 0, padding))
        if size is not None and cursize + chunksize >= size:
            chunk = chunk[:chunksize - (cursize - size)]
            archipelagoobject.sync_write(chunk)
            cursize += len(chunk)
            break
        archipelagoobject.sync_write(chunk)
        padding = chunksize - len(chunk)

    padding = size - cursize if size is not None else 0
    if padding <= 0:
        return

    q, r = divmod(padding, chunksize)
    for x in xrange(q):
        archipelagoobject.sync_write(zeros(chunksize))
    archipelagoobject.sync_write(buffer(zeros(chunksize), 0, r))


def file_sync_read_chunks(archipelagoobject, chunksize, nr, offset=0):
    """Read and yield groups of chunks from a buffered file object at offset.
       Reads never span accros chunksize boundaries.
    """
    archipelagoobject.seek(offset * chunksize)
    while nr:
        remains = chunksize
        chunk = ''
        while 1:
            s = archipelagoobject.sync_read(remains)
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


class ArchipelagoObject(object):
    __slots__ = ("name", "ioctx_pool", "dst_port", "create", "offset")

    def __init__(self, name, ioctx_pool, dst_port=None, create=0):
        self.name = name
        self.ioctx_pool = ioctx_pool
        self.create = create
        self.dst_port = dst_port
        self.offset = 0

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
        raise NotImplementedError("File truncation is not implemented yet \
                                   in archipelago")

    def sync_write(self, data):
        ioctx = self.ioctx_pool.pool_get() 
        req = Request.get_write_request(ioctx, self.dst_port, self.name,
                                        data=data, offset=self.offset,
                                        datalen=len(data))
        req.submit()
        req.wait()
        ret = req.success()
        req.put()
        self.ioctx_pool.pool_put(ioctx)
        if ret:
            self.offset += len(data)
        else:
            raise IOError("archipelago: Write request error")

    def sync_write_chunks(self, chunksize, offset, chunks, size=None):
        return file_sync_write_chunks(self, chunksize, offset, chunks,size)

    def sync_read(self, size):
        read = Request.get_read_request
        data = ''
        datalen = 0
        dsize = size
        while 1:
            ioctx = self.ioctx_pool.pool_get() 
            req = read(ioctx, self.dst_port,
                       self.name,size=dsize-datalen,offset=self.offset)
            req.submit()
            req.wait()
            ret = req.success()
            if ret:
                s = string_at(req.get_data(),dsize-datalen)
            else:
                s = None
            req.put()
            self.ioctx_pool.pool_put(ioctx)
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
