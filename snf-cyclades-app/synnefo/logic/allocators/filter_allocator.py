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

from __future__ import division
import logging

from synnefo.logic.allocators.base import AllocatorBase
from django.conf import settings
from django.utils import importlib


log = logging.getLogger(__name__)


class FilterAllocator(AllocatorBase):
    filters = None

    def __init__(self, filter_modules=None):
        filters = []
        if filter_modules is None:
            filter_modules = settings.BACKEND_FILTER_ALLOCATOR_FILTERS

        for fm in filter_modules:
            path, filter_class = fm.rsplit('.', 1)
            module = importlib.import_module(path)
            filter = getattr(module, filter_class)()
            filters.append(filter)

        self.filters = filters

    def filter_backends(self, backends, vm):
        """
        Run each backend filter in the specified order.
        """
        for filter in self.filters:
            backends = filter.filter_backends(backends, vm)
            if not backends:
                return backends

        return backends

    def allocate(self, backends, vm):
        """
        Choose the 'best' backend for the VM.
        """
        if len(backends) == 1:
            return backends[0]

        # Compute the scores for each backend
        backend_scores = [(backend, self.backend_score(backend))
                          for backend in backends]

        log.debug("Backend scores %s", backend_scores)

        # Pick out the best
        result = min(backend_scores, key=lambda (b, b_score): b_score)
        backend = result[0]

        return backend

    def backend_score(self, backend):
        """
        Score a backend based on available memory, disk size and cpu ratio.
        """
        mem_ratio = 0
        disk_ratio = 0
        cpu_ratio = 1

        if backend.mtotal:
            mem_ratio = 1 - (backend.mfree / backend.mtotal)
        if backend.dtotal:
            disk_ratio = 1 - (backend.dfree / backend.dtotal)
        if backend.ctotal:
            cpu_ratio = ((backend.pinst_cnt + 1) * 4) / (backend.ctotal * 3)

        return 0.5 * cpu_ratio + 0.5 * (mem_ratio + disk_ratio)
