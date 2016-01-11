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

    # Compute the scores for each backend
    backend_scores = [(backend, backend_score(backend, vm))
                      for backend in backends]

    log.debug("Backend scores %s", backend_scores)

    # Pick out the best
    result = min(backend_scores, key=lambda (b, b_score): b_score)
    backend = result[0]

    return backend


def backend_score(backend, flavor):
    mem_ratio = 1 - (backend.mfree / backend.mtotal) if backend.mtotal else 0
    disk_ratio = 1 - (backend.dfree / backend.dtotal) if backend.dtotal else 0
    if backend.ctotal:
        cpu_ratio = ((backend.pinst_cnt + 1) * 4) / (backend.ctotal * 3)
    else:
        cpu_ratio = 1
    return 0.5 * cpu_ratio + 0.5 * (mem_ratio + disk_ratio)
