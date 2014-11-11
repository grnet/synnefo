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

"""
This is the burnin class that tests the Projects functionality

"""

import random

from synnefo_tools.burnin.common import Proper
from synnefo_tools.burnin.cyclades_common import CycladesTests, \
    QADD, QREMOVE, MB, GB, QDISK, QVM, QRAM, QCPU


# pylint: disable=too-many-public-methods
class QuotasTestSuite(CycladesTests):
    """Test Quotas functionality"""
    server = Proper(value=None)

    def test_001_check_skip(self):
        """Check if we are members in more than one projects"""
        self._skip_suite_if(len(self.quotas.keys()) < 2,
                            "This user is not a member of 2 or more projects")

    def test_002_create(self):
        """Create a machine to a different project than base"""
        image = random.choice(self._parse_images())
        flavors = self._parse_flavors()

        # We want to create our machine in a project other than 'base'
        projects = self.quotas.keys()
        projects.remove(self._get_uuid())
        (flavor, project) = self._find_project(flavors, projects)

        # Create machine
        self.server = self._create_server(image, flavor, network=True,
                                          project_id=project)

        # Wait for server to become active
        self._insist_on_server_transition(
            self.server, ["BUILD"], "ACTIVE")

    def test_003_assign(self):
        """Re-Assign the machine to a different project"""
        # We will use the base project for now
        new_project = self._get_uuid()
        project_name = self._get_project_name(new_project)
        self.info("Assign %s to project %s", self.server['name'], project_name)

        # Reassign server
        old_project = self.server['tenant_id']
        self.clients.cyclades.reassign_server(self.server['id'], new_project)

        # Check tenant_id
        self.server = self._get_server_details(self.server, quiet=True)
        self.assertEqual(self.server['tenant_id'], new_project)

        # Check new quotas
        flavor = self.clients.compute.get_flavor_details(
            self.server['flavor']['id'])
        changes = \
            {old_project:
                [(QDISK, QREMOVE, flavor['disk'], GB),
                 (QVM, QREMOVE, 1, None),
                 (QRAM, QREMOVE, flavor['ram'], MB),
                 (QCPU, QREMOVE, flavor['vcpus'], None)],
             new_project:
                [(QDISK, QADD, flavor['disk'], GB),
                 (QVM, QADD, 1, None),
                 (QRAM, QADD, flavor['ram'], MB),
                 (QCPU, QADD, flavor['vcpus'], None)]}
        self._check_quotas(changes)

    def test_004_cleanup(self):
        """Remove test server"""
        self._delete_servers([self.server])
