# -*- coding: utf-8 -
#
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

from pithos.workers import glue
import pickle
from svipc import sem_init, sem_take, sem_give

def find_hole(WORKERS, FOLLOW_WORKERS):
        old_key = []
        old_age =  []
        for key in FOLLOW_WORKERS:
                if key not in WORKERS.keys():
                        old_age.append(FOLLOW_WORKERS[key] )
                        old_key.append( key )
                        break
        if len(old_age) and len(old_key):
                for key in old_key:
                        del FOLLOW_WORKERS[key]
                return old_age
        return old_age

def follow_workers(pid, wid, WORKERS):
        hole = None
        try:
                fd = open('/dev/shm/wid','rb')
                f = pickle.load(fd)
                hole = find_hole(WORKERS, f)
                if len(hole) > 0:
                    k = {pid: int(hole[0])}
                else:
                    k = {pid: wid}
                f.update(k)
                fd.close()
                fd = open('/dev/shm/wid','wb')
                pickle.dump(f, fd)
                fd.close()
        except:
                fd = open('/dev/shm/wid','wb')
                pickle.dump({pid:wid}, fd)
                fd.close()
        return hole

def allocate_wid(pid, wid, WORKERS):
        d = {pid: wid}
        hole = None
        if sem_init(88,nums=1) == 0:
                hole = follow_workers(pid, wid, WORKERS)
                sem_give(88,0)
        else:
                sem_take(88,0)
                hole = follow_workers(pid, wid, WORKERS)
                sem_give(88,0)
        return hole


def post_fork(server,worker):
        wid = allocate_wid(worker.pid,worker.worker_id, server.WORKERS)
        if wid:
                glue.WorkerGlue.setmap(worker.pid,wid[0])
        else:
                glue.WorkerGlue.setmap(worker.pid,worker.worker_id)

