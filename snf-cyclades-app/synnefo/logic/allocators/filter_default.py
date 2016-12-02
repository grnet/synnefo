# Copyright (C) 2010-2016 GRNET S.A.
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

import logging
from synnefo.logic.allocators.filter_base import FilterBase

log = logging.getLogger(__name__)


class DefaultFilter(FilterBase):

    def filter_backends(self, backends, vm):
        """
        Filter backends based on the backend statistics. Consider only Backends
        that can host the VM based on Cyclades temporary stats.

        Since the stats are not entirely up to date, if no backends can host
        the VMs, this filter is a no-op.
        """
        # Filter those that cannot host the vm
        capable_backends = [backend for backend in backends
                            if self.vm_fits_in_backend(backend, vm)]

        log.debug("Capable backends for VM %s: %s", vm, capable_backends)

        # Since we are conservatively updating backend resources on each
        # allocation, a backend may actually be able to host a vm (despite
        # the state of the backend in db)
        if not capable_backends:
            log.debug("No backend that can host the VM found. Returning all.")
            capable_backends = backends

        return capable_backends

    def vm_fits_in_backend(self, backend, vm):
        has_disk = backend.dfree > vm['disk']
        has_mem = backend.mfree > vm['ram']
        # Consider each VM having 4 Virtual CPUs
        vcpu_ratio = ((backend.pinst_cnt + 1) * 4) / backend.ctotal
        # Consider max vcpu/cpu ratio 3
        has_cpu = vcpu_ratio < 3

        return has_cpu and has_disk and has_mem
