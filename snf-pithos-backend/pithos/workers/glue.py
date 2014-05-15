# -*- coding: utf-8 -
#
# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import ConfigParser


class WorkerGlue(object):

    pmap = {}
    worker_id = None
    ioctx_pool = None
    ArchipelagoConfFile = None

    @classmethod
    def setmap(cls, pid, index):
        WorkerGlue.pmap[pid] = index
        WorkerGlue.worker_id = index

    @classmethod
    def setupXsegPool(cls, ObjectPool, Segment, Xseg_ctx,
                      cfile='/etc/archipelago/archipelago.conf', pool_size=8):
        if WorkerGlue.ioctx_pool is not None:
            return
        bcfg = ConfigParser.ConfigParser()
        bcfg.readfp(open(cfile))
        worker_id = WorkerGlue.worker_id
        WorkerGlue.ArchipelagoConfFile = cfile
        archipelago_segment_type = 'posix'
        archipelago_segment_name = 'archipelago'
        archipelago_dynports = bcfg.getint('XSEG', 'SEGMENT_DYNPORTS')
        archipelago_ports = bcfg.getint('XSEG', 'SEGMENT_PORTS')
        archipelago_segment_size = bcfg.getint('XSEG', 'SEGMENT_SIZE')
        archipelago_segment_alignment = 12

        class XsegPool(ObjectPool):

            def __init__(self):
                super(XsegPool, self).__init__(size=pool_size)
                self.segment = Segment(archipelago_segment_type,
                                       archipelago_segment_name,
                                       archipelago_dynports,
                                       archipelago_ports,
                                       archipelago_segment_size,
                                       archipelago_segment_alignment)
                self.worker_id = worker_id
                self.cnt = 1

            def _pool_create(self):
                if self.worker_id == 1:
                    ioctx = Xseg_ctx(self.segment, self.worker_id + self.cnt)
                    self.cnt += 1
                    return ioctx
                elif self.worker_id > 1:
                    ioctx = Xseg_ctx(self.segment,
                                     (self.worker_id - 1) * pool_size + 2 +
                                     self.cnt)
                    self.cnt += 1
                    return ioctx
                elif self.worker_id is None:
                    ioctx = Xseg_ctx(self.segment)
                    return ioctx

            def _pool_verify(self, poolobj):
                return True

            def _pool_cleanup(self, poolobj):
                return False

        WorkerGlue.ioctx_pool = XsegPool()
