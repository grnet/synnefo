# Copyright (C) 2010-2015 GRNET S.A.
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


import django.test
from django.test.utils import override_settings
from synnefo.volume import util
from snf_django.lib.api import faults
from synnefo.db import models_factory as mf


mock_templates = ("template1", "template2")


class MockVolumeType(object):

    def __init__(self, disk_template):
        self.disk_template = disk_template
        self.name = "name_" + disk_template


class DetachableVolumeTypesTest(django.test.TestCase):

    """Test utils for detachable volume types."""

    missing_msg = "Volume type must be provided"
    wrong_msg = "Volume type 'name_template3' is not detachable"

    @override_settings(CYCLADES_DETACHABLE_DISK_TEMPLATES=mock_templates)
    def test_detachable_volumes_utils(self):
        # No volume type
        volume_type = None
        with self.assertRaisesMessage(faults.BadRequest, self.missing_msg):
            util.is_volume_type_detachable(volume_type)

        # Non-detachable template
        volume_type = MockVolumeType("template3")
        self.assertEqual(util.is_volume_type_detachable(volume_type), False)

        # Detachable template
        volume_type = MockVolumeType("template2")
        self.assertEqual(util.is_volume_type_detachable(volume_type), True)

        # Non-detachable template and assert
        volume_type = MockVolumeType("template3")
        with self.assertRaisesMessage(faults.BadRequest, self.wrong_msg):
            util.assert_detachable_volume_type(volume_type)

        # Detachable template and assert
        volume_type = MockVolumeType("template1")
        util.assert_detachable_volume_type(volume_type)


class VolumeUtilsTest(django.test.TestCase):

    """Various tests for volume utils."""

    wrong_msg = "Cannot set the index of volume '%s' to '%s', since it is" \
                " used by another volume of server '%s'."

    def test_assign_to_server(self):
        """Test if volume assignment to server works properly."""
        vm = mf.VirtualMachineFactory()

        # Assign a volume to a server with no volumes.
        vol1 = mf.VolumeFactory()
        util.assign_volume_to_server(vm, vol1)
        # Assert that the volume is associated with the server and that its
        # index is 0.
        self.assertEqual(vol1.machine, vm)
        self.assertItemsEqual(vm.volumes.all(), [vol1])
        self.assertEqual(vol1.index, 0)

        # Assign a volume to a server with a volume.
        vol2 = mf.VolumeFactory()
        util.assign_volume_to_server(vm, vol2)
        # Assert that the volume is associated with the server and that its
        # index is 1.
        self.assertEqual(vol2.machine, vm)
        self.assertItemsEqual(vm.volumes.all(), [vol1, vol2])
        self.assertEqual(vol2.index, 1)

        # Assign a volume to a server with more than one volume and set its
        # index to a custom value (e.g. 9)
        vol3 = mf.VolumeFactory()
        util.assign_volume_to_server(vm, vol3, index=9)
        # Assert that the volume is associated with the server and that its
        # index is set to 9.
        self.assertEqual(vol3.machine, vm)
        self.assertItemsEqual(vm.volumes.all(), [vol1, vol2, vol3])
        self.assertEqual(vol3.index, 9)

        # Assign a volume to a server with a volume whose index is 1 and a
        # deleted volume whose index is 9.
        vol1.machine = None
        vol1.save()
        vol3.deleted = True
        vol3.save()
        vol4 = mf.VolumeFactory()
        util.assign_volume_to_server(vm, vol4)
        # Assert that the volume is associated with the server and that its
        # index is 2.
        self.assertEqual(vol4.machine, vm)
        self.assertItemsEqual(vm.volumes.filter(deleted=False), [vol2, vol4])
        self.assertEqual(vol4.index, 2)

        # Assert that the same index cannot be assigned to a different volume.
        vol5 = mf.VolumeFactory()
        with self.assertRaisesMessage(faults.BadRequest,
                                      self.wrong_msg.format(vol5, 2, vm)):
            util.assign_volume_to_server(vm, vol5, index=2)

    def test_get_server(self):
        """Test if `get_server` works properly."""
        # The user id for this test.
        user_id = "test_user"

        # Fail to get server that belongs to another user
        vm = mf.VirtualMachineFactory(userid="other_user")
        not_found_msg = "Server %s not found" % vm.id
        with self.assertRaisesMessage(faults.ItemNotFound, not_found_msg):
            util.get_server(user_id, vm.pk)

        # Fail to get server with non-existent id
        server_id = 1134
        not_found_msg = "Server %s not found" % server_id
        with self.assertRaisesMessage(faults.ItemNotFound, not_found_msg):
            util.get_server(user_id, server_id)

        # Fail to get server with invalid id
        server_id = "could this BE any less int?"
        invalid_msg = "Invalid server id: %s" % server_id
        with self.assertRaisesMessage(faults.BadRequest, invalid_msg):
            util.get_server(user_id, server_id)

        # Successfully get own server
        vm = mf.VirtualMachineFactory(userid=user_id)
        self.assertEqual(vm, util.get_server(user_id, vm.pk))

    def test_get_volume_type(self):
        """Test if `get_volume_type` works properly."""
        # Fail to get volume type with non-existent id
        vt_id = 1134
        not_found_msg = "Volume type %s not found" % vt_id
        with self.assertRaisesMessage(faults.ItemNotFound, not_found_msg):
            util.get_volume_type(vt_id)

        # Fail to get volume type with invalid id
        vt_id = "could this BE any less int?"
        invalid_msg = "Invalid volume id: %s" % vt_id
        with self.assertRaisesMessage(faults.BadRequest, invalid_msg):
            util.get_volume_type(vt_id)

        # Success case
        vt = mf.VolumeTypeFactory()
        self.assertEqual(vt, util.get_volume_type(vt.id))
