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
from pithos.workers import glue
from multiprocessing import Lock
import mmap
import pickle
import os

SYNNEFO_UMASK=0o007

def find_hole(workers, fworkers):
    old_key = []
    old_age = []
    for key in fworkers:
        if key not in workers.keys():
                old_age.append(fworkers[key])
                old_key.append(key)
                break
    if len(old_age) and len(old_key):
        for key in old_key:
            del fworkers[key]
        return old_age
    return old_age


def follow_workers(pid, wid, server):
    hole = None
    fd = server.state_fd
    fd.seek(0)
    f = pickle.load(fd)
    hole = find_hole(server.WORKERS, f)
    if len(hole) > 0:
        k = {pid: int(hole[0])}
    else:
        k = {pid: wid}
    f.update(k)
    fd.seek(0)
    pickle.dump(f, fd)
    return hole


def allocate_wid(pid, wid, server):
    hole = None
    hole = follow_workers(pid, wid, server)
    return hole


def when_ready(server):
    server.lock = Lock()
    server.state_fd = mmap.mmap(-1, 4096)
    pickle.dump({}, server.state_fd)


def update_workers(pid, wid, server):
    fd = server.state_fd
    fd.seek(0)
    f = pickle.load(fd)
    for k, v in f.items():
        if wid == v:
            del f[k]
            break
    k = {pid: wid}
    f.update(k)
    fd.seek(0)
    pickle.dump(f, fd)


def post_fork(server, worker):
    # set umask for the gunicorn worker
    os.umask(SYNNEFO_UMASK)
    server.lock.acquire()
    if server.worker_age <= server.num_workers:
        update_workers(worker.pid, server.worker_age, server)
        glue.WorkerGlue.setmap(worker.pid, server.worker_age)
    else:
        wid = allocate_wid(worker.pid, server.worker_age, server)
        glue.WorkerGlue.setmap(worker.pid, wid[0])
    server.lock.release()


def worker_exit(server, worker):
    if glue.WorkerGlue.ioctx_pool:
        glue.WorkerGlue.ioctx_pool._shutdown_pool()


def on_exit(server):
    server.state_fd.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
