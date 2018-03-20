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
This is the burnin class that tests the Volumes functionality

"""

import random

from synnefo_tools.burnin.common import Proper
from synnefo_tools.burnin.cyclades_common import CycladesTests


class VolumeTestSuite(CycladesTests):
    detachable_vlm_t = Proper(value=None)
    non_detachable_vlm_t = Proper(value=None)

    detachable_vlm_flavors = Proper(value=None)
    non_detachable_vlm_flavors = Proper(value=None)

    use_image = Proper(value=None)

    server = Proper(value=None)
    second_server = Proper(value=None)
    detachable_volume = Proper(value=None)
    non_detachable_volume = Proper(value=None)

    def test_000_set_up(self):
        self.detachable_vlm_t, self.non_detachable_vlm_t = \
            self._parse_volume_types()
        self.detachable_vlm_flavors, self.non_detachable_vlm_flavors = \
            self._parse_volume_flavors(self.detachable_vlm_t,
                                       self.non_detachable_vlm_t)
        self.use_image = random.choice(self._parse_images())

    """ Detachable Volume Tests"""
    def test_001_create_and_destroy_volume(self):
        """Test create and destroy a detachable volume"""
        created_volume = self._create_detachable_volume(
                self.detachable_vlm_t, size=5)
        self.detachable_volume = self._get_volume_details(created_volume)
        self._destroy_volume(self.detachable_volume)

    def test_002_create_detachable_volume(self):
        """Test create a detachable volume"""
        created_volume = self._create_detachable_volume(
                self.detachable_vlm_t, size=5)
        self.detachable_volume = self._get_volume_details(created_volume)

    def test_003_attach_volume(self):
        """Test attach a detachable volume to a VM"""
        use_flavor = random.choice(self.detachable_vlm_flavors)

        self.server = self._create_server(self.use_image, use_flavor)
        self._insist_on_server_transition(self.server, ["BUILD"], "ACTIVE")

        # Initially only one volume should be attached(boot volume)
        attached_volumes = self._get_attached_volumes(self.server)
        self.assertEqual(len(attached_volumes), 1)

        # Attach the created volume
        self._attach_volume(self.server, self.detachable_volume)

        attached_volumes = self._get_attached_volumes(self.server)
        # Make sure it is attached
        self.assertEqual(len(attached_volumes), 2)
        volume_attached = False
        for volume in attached_volumes:
            if str(volume['id']) == str(self.detachable_volume['id']):
                volume_attached = True
        self.assertTrue(volume_attached)

    def test_004_detach_volume(self):
        """Test detach a detachable volume from a VM"""
        self._detach_volume(self.server, self.detachable_volume)
        attached_volumes = self._get_attached_volumes(self.server)

        # Make sure it is attached
        self.assertEqual(len(attached_volumes), 1)
        volume_detached = True
        for volume in attached_volumes:
            if str(volume['id']) == str(self.detachable_volume['id']):
                volume_detached = False
        self.assertTrue(volume_detached)

    def test_005_re_attach_volume(self):
        """Test re attach a detachable volume to a different VM"""
        use_flavor = random.choice(self.detachable_vlm_flavors)

        self.second_server = self._create_server(self.use_image, use_flavor)
        self._insist_on_server_transition(self.second_server,
                                          ["BUILD"], "ACTIVE")

        # Initially only one volume should be attached(boot volume)
        attached_volumes = self._get_attached_volumes(self.second_server)
        self.assertEqual(len(attached_volumes), 1)

        # Attach the created volume
        self._attach_volume(self.second_server, self.detachable_volume)

        attached_volumes = self._get_attached_volumes(self.second_server)
        # Make sure it is attached
        self.assertEqual(len(attached_volumes), 2)
        volume_attached = False
        for volume in attached_volumes:
            if str(volume['id']) == str(self.detachable_volume['id']):
                volume_attached = True
        self.assertTrue(volume_attached)

    def test_006_detach_re_attached_volume(self):
        """Test detach the re attached detachable volume"""
        self._detach_volume(self.second_server, self.detachable_volume)
        attached_volumes = self._get_attached_volumes(self.second_server)

        # Make sure it is attached
        self.assertEqual(len(attached_volumes), 1)
        volume_detached = True
        for volume in attached_volumes:
            if str(volume['id']) == str(self.detachable_volume['id']):
                volume_detached = False
        self.assertTrue(volume_detached)

    def test_007_destroy_volume(self):
        """Test destroy the detached detachable volume"""
        self._destroy_volume(self.detachable_volume)
        self._delete_servers([self.server, self.second_server])

    """Non detachable volumes tests"""
    def test_008_create_non_detachable_volume(self):
        """Test create non detachable volume"""
        use_flavor = random.choice(self.non_detachable_vlm_flavors)
        self.server = self._create_server(self.use_image, use_flavor)
        self._insist_on_server_transition(self.server, ["BUILD"], "ACTIVE")

        # Initially only one volume should be attached(boot volume)
        attached_volumes = self._get_attached_volumes(self.server)
        self.assertEqual(len(attached_volumes), 1)

        created_volume = self._create_non_detachable_volume(
                self.non_detachable_vlm_t, size=5,
                server_id=self.server['id'])
        self.non_detachable_volume = self._get_volume_details(created_volume)

        attached_volumes = self._get_attached_volumes(self.server)
        # Make sure it is attached
        self.assertEqual(len(attached_volumes), 2)
        volume_attached = False
        for volume in attached_volumes:
            if str(volume['id']) == str(self.non_detachable_volume['id']):
                volume_attached = True
        self.assertTrue(volume_attached)

    def test_009_destroy_non_detachable_volume(self):
        """Test destroy a non detachable volume"""
        self._destroy_volume(self.non_detachable_volume)
        self._delete_servers([self.server])
