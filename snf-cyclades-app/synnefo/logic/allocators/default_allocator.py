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

from __future__ import division
import logging


log = logging.getLogger(__name__)


def allocate(backends, vm):
    if len(backends) == 1:
        return backends[0]

    # Filter those that cannot host the vm
    capable_backends = [backend for backend in backends
                        if vm_fits_in_backend(backend, vm)]

    log.debug("Capable backends for VM %s: %s", vm, capable_backends)

    # Since we are conservatively updating backend resources on each
    # allocation, a backend may actually be able to host a vm (despite
    # the state of the backend in db)
    if not capable_backends:
        capable_backends = backends

    # Compute the scores for each backend
    backend_scores = [(backend, backend_score(backend, vm))
                      for backend in capable_backends]

    log.debug("Backend scores %s", backend_scores)

    # Pick out the best
    result = min(backend_scores, key=lambda (b, b_score): b_score)
    backend = result[0]

    return backend


def vm_fits_in_backend(backend, vm):
    has_disk = backend.dfree > vm['disk']
    has_mem = backend.mfree > vm['ram']
    # Consider each VM having 4 Virtual CPUs
    vcpu_ratio = ((backend.pinst_cnt + 1) * 4) / backend.ctotal
    # Consider max vcpu/cpu ratio 3
    has_cpu = vcpu_ratio < 3
    return has_cpu and has_disk and has_mem


def backend_score(backend, flavor):
    mem_ratio = 1 - (backend.mfree / backend.mtotal) if backend.mtotal else 0
    disk_ratio = 1 - (backend.dfree / backend.dtotal) if backend.dtotal else 0
    if backend.ctotal:
        cpu_ratio = ((backend.pinst_cnt + 1) * 4) / (backend.ctotal * 3)
    else:
        cpu_ratio = 1
    return 0.5 * cpu_ratio + 0.5 * (mem_ratio + disk_ratio)
