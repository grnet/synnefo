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
The tests require at least *two* projects to run.
The second project (the first is the system or base one) should have
at least the following resources assigned to it:
- 2 VMs
- 2 CPUs
- 1 GB RAM
- 4GB hard disk
- 2 floating IPs
The project can be created through the UI with the default user
(user@synnefo.org) and can be activated with the command
snf-manage project-control --approve <application id>
The application id can be retrieved with the command snf-manage project-list
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

    def test_002a_create_in_default_project(self):
        """Set default project to assign new resources"""
        image = random.choice(self._parse_images())
        flavors = self._parse_flavors()
        user_id = self._get_uuid()

        # We want to create our machine in the default project,
        # which is not the base one
        projects = self.quotas.keys()
        projects.remove(user_id)
        (flavor, project_id) = self._find_project(flavors, projects)

        # Set default project: a project other than the base one
        self.info("Set default project: %s", project_id)
        self.clients.astakos.set_default_project(project_id)

        # Create machine
        self.server = self._create_server(image, flavor, network=True)

        # Wait for server to become active
        self._insist_on_server_transition(
            self.server, ["BUILD"], "ACTIVE")

        # Check tenant_id
        self.server = self._get_server_details(self.server, quiet=True)
        self.assertEqual(self.server['tenant_id'], project_id)

    def test_002b_create_in_provided_project(self):
        """Create a machine and assign it to a different project than base"""
        image = random.choice(self._parse_images())
        flavors = self._parse_flavors()
        user_id = self._get_uuid()

        # Set default project: the base one to secure the test's integrity
        self.clients.astakos.set_default_project(user_id)

        # We want to create our machine in a project other than 'base'
        projects = self.quotas.keys()
        projects.remove(user_id)
        (flavor, project_id) = self._find_project(flavors, projects)

        # Create machine
        self.server = self._create_server(image, flavor, network=True,
                                          project_id=project_id)

        # Wait for server to become active
        self._insist_on_server_transition(
            self.server, ["BUILD"], "ACTIVE")

        # Check tenant_id
        self.server = self._get_server_details(self.server, quiet=True)
        self.assertEqual(self.server['tenant_id'], project_id)

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
