# Copyright (C) 2010-2017 GRNET S.A.
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
This is the burnin class that tests the Keypairs functionality

"""
from synnefo_tools.burnin.common import Proper
from synnefo_tools.burnin.cyclades_common import CycladesTests

import random



class KeypairsTestSuite(CycladesTests):

    server = Proper(value=None)
    generated_keypair = Proper(value=None)
    uploaded_keypair = Proper(value=None)

    def test_001_create_keypair(self):
        self.generated_keypair = self._generate_keypair()
        keypairs = self._get_keypairs()
        keypair_added = False
        for keypair in keypairs:
            if keypair['name'] == self.generated_keypair['name']:
                keypair_added = True
                break
        self.assertTrue(keypair_added)

    def test_002_upload_keypair(self):
        paramiko_keypair = paramiko.RSAKey.generate(2048)
        self.uploaded_keypair = self._upload_keypair(public_key="ssh-rsa %s" %
                paramiko_keypair.get_base64())
        keypairs = self._get_keypairs()
        keypair_added = False
        for keypair in keypairs:
            if keypair['name'] == self.uploaded_keypair['name']:
                keypair_added = True
                break
        self.assertTrue(keypair_added)

    def test_003_create_server_with_ssh_keypairs(self):
        use_flavor = random.choice(self._parse_flavors())
        use_image = random.choice(self._parse_images())
        self.server = self._create_server(use_image, use_flavor,
                key_name=self.generated_keypair['name'], network=True)
        self._insist_on_server_transition(self.server, ["BUILD"], "ACTIVE")

    def test_004_ssh_to_server_with_generated_key(self):
        self._insist_on_ip_attached(self.server)
        ipv4 = self._get_server_details(self.server)['attachments'][0]['ipv4']
        self._insist_get_hostname_over_ssh(ipv4, username="root",
            private_key=self.generated_keypair['private_key'])

    def test_005_clean_up(self):
        self._delete_keypair(self.generated_keypair)
        self._delete_keypair(self.uploaded_keypair)
        self._delete_servers([self.server])
