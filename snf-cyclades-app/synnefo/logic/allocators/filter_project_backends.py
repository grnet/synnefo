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
from synnefo.db.models import Backend

log = logging.getLogger(__name__)


class ProjectBackendsFilter(FilterBase):

    def filter_backends(self, backends, vm):
        """
        Filter backends based on the assigned backends for the VM's project.

        If the project has assigned VMs consider only those for possible
        allocation.

        Otherwise return only the public backends.
        """
        project = vm['project']
        project_backends = list(Backend.objects
                                .filter(projects__project=project))
        if project_backends:
            log.debug("Project {0} is assigned to these backends: {1}"
                      .format(project, project_backends))
            # Consider only available backends
            backends = list(set(backends).intersection(project_backends))
        else:
            log.debug("Project {0} does not have any backends assigned. "
                      "Returning public backends".format(project))
            backends = filter(lambda b:  b.public, backends)

        log.debug("Filtered backends: {0}".format(backends))

        return backends
