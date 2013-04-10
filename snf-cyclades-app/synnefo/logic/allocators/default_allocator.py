# Copyright 2011 GRNET S.A. All rights reserved.
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

from __future__ import division
import logging


log = logging.getLogger(__name__)


def allocate(backends, vm):
    if len(backends) == 1:
        return backends[0]

    # Filter those that can not host the vm
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
    mem_ratio = 1 - (backend.mfree / backend.mtotal)
    disk_ratio = 1 - (backend.dfree / backend.dtotal)
    cpu_ratio = ((backend.pinst_cnt + 1) * 4) / (backend.ctotal * 3)
    return 0.5 * cpu_ratio + 0.5 * (mem_ratio + disk_ratio)
