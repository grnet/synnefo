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

from snf_django.utils.testing import BaseAPITest, mocked_quotaholder
#from synnefo.db.models import Volume
from synnefo.db import models_factory as mf
from synnefo.volume import volumes
from snf_django.lib.api import faults
from mock import patch
from copy import deepcopy


@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class VolumesTest(BaseAPITest):
    def setUp(self):
        self.userid = "test_user"
        self.size = 1
        self.vm = mf.VirtualMachineFactory(
            userid=self.userid,
            flavor__disk_template="ext_archipelago")
        self.kwargs = {"user_id": self.userid,
                       "size": self.size,
                       "server_id": self.vm.id}

    def test_create(self, mrapi):
        # No server id
        kwargs = deepcopy(self.kwargs)
        kwargs["server_id"] = None
        self.assertRaises(faults.BadRequest,
                          volumes.create,
                          **kwargs)

        # Invalid server
        vm = mf.VirtualMachineFactory(userid="other_user")
        kwargs["server_id"] = vm.id
        self.assertRaises(faults.BadRequest,
                          volumes.create,
                          **kwargs)

        # Create server without source!
        mrapi().ModifyInstance.return_value = 42
        with mocked_quotaholder():
            vol = volumes.create(**self.kwargs)

        self.assertEqual(vol.size, self.size)
        self.assertEqual(vol.userid, self.userid)
        self.assertEqual(vol.name, None)
        self.assertEqual(vol.description, None)
        self.assertEqual(vol.source_snapshot_id, None)
        self.assertEqual(vol.source, None)
        self.assertEqual(vol.origin, None)
        self.assertEqual(vol.source_volume_id, None)
        self.assertEqual(vol.source_image_id, None)
        self.assertEqual(vol.machine, self.vm)

        name, args, kwargs = mrapi().ModifyInstance.mock_calls[0]
        self.assertEqual(kwargs["instance"], self.vm.backend_vm_id)
        disk_info = kwargs["disks"][0][2]
        self.assertEqual(disk_info["size"], self.size << 10)
        self.assertEqual(disk_info["name"], vol.backend_volume_uuid)
        self.assertFalse("origin" in disk_info)

    def test_create_from_volume(self, mrapi):
        # Check permissions
        svol = mf.VolumeFactory(userid="other_user")
        self.assertRaises(faults.BadRequest,
                          volumes.create,
                          source_volume_id=svol.id,
                          **self.kwargs)
        # Invalid volume status
        svol = mf.VolumeFactory(userid=self.userid, status="CREATING")
        self.assertRaises(faults.BadRequest,
                          volumes.create,
                          source_volume_id=svol.id,
                          **self.kwargs)
        svol = mf.VolumeFactory(userid=self.userid, status="AVAILABLE")
        self.assertRaises(faults.BadRequest,
                          volumes.create,
                          source_volume_id=svol.id,
                          **self.kwargs)

        svol.status = "IN_USE"
        svol.save()
        mrapi().ModifyInstance.return_value = 42
        kwargs = deepcopy(self.kwargs)
        kwargs["size"] = svol.size
        with mocked_quotaholder():
            vol = volumes.create(source_volume_id=svol.id, **kwargs)

        self.assertEqual(vol.size, svol.size)
        self.assertEqual(vol.userid, self.userid)
        self.assertEqual(vol.name, None)
        self.assertEqual(vol.description, None)
        self.assertEqual(vol.source, "volume:%s" % svol.id)
        self.assertEqual(vol.origin, svol.backend_volume_uuid)

        name, args, kwargs = mrapi().ModifyInstance.mock_calls[0]
        self.assertEqual(kwargs["instance"], self.vm.backend_vm_id)
        disk_info = kwargs["disks"][0][2]
        self.assertEqual(disk_info["size"], svol.size << 10)
        self.assertEqual(disk_info["name"], vol.backend_volume_uuid)
        self.assertEqual(disk_info["origin"], svol.backend_volume_uuid)

    @patch("synnefo.plankton.backend.PlanktonBackend")
    def test_create_from_snapshot(self, mimage, mrapi):
        # Wrong source
        mimage().__enter__().get_snapshot.side_effect = faults.ItemNotFound
        self.assertRaises(faults.BadRequest,
                          volumes.create,
                          source_snapshot_id=421,
                          **self.kwargs)

        mimage().__enter__().get_snapshot.side_effect = None
        mimage().__enter__().get_snapshot.return_value = {
            'location': 'pithos://foo',
            'mapfile': 'snf-snapshot-43',
            'id': 12,
            'name': "test_image",
            'size': 1242,
            'disk_format': 'diskdump',
            'status': 'AVAILABLE',
            'properties': {'source_volume': 42}}

        mrapi().ModifyInstance.return_value = 42
        with mocked_quotaholder():
            vol = volumes.create(source_snapshot_id=12, **self.kwargs)

        self.assertEqual(vol.size, self.size)
        self.assertEqual(vol.userid, self.userid)
        self.assertEqual(vol.name, None)
        self.assertEqual(vol.description, None)
        self.assertEqual(int(vol.source_snapshot_id), 12)
        self.assertEqual(vol.source_volume_id, None)
        self.assertEqual(vol.source_image_id, None)
        self.assertEqual(vol.origin, "snf-snapshot-43")

        name, args, kwargs = mrapi().ModifyInstance.mock_calls[0]
        self.assertEqual(kwargs["instance"], self.vm.backend_vm_id)
        disk_info = kwargs["disks"][0][2]
        self.assertEqual(disk_info["size"], self.size << 10)
        self.assertEqual(disk_info["name"], vol.backend_volume_uuid)
        self.assertEqual(disk_info["origin"], "snf-snapshot-43")

    def test_delete(self, mrapi):
        # We can not deleted detached volumes
        vol = mf.VolumeFactory(machine=None, status="AVAILABLE")
        self.assertRaises(faults.BadRequest,
                          volumes.delete,
                          vol)

        vm = mf.VirtualMachineFactory()
        # Also we cannot delete root volume
        vol.index = 0
        vol.machine = vm
        vol.status = "IN_USE"
        vol.save()
        self.assertRaises(faults.BadRequest,
                          volumes.delete,
                          vol)

        # We can delete everything else
        vol.index = 1
        mrapi().ModifyInstance.return_value = 42
        with mocked_quotaholder():
            volumes.delete(vol)
        self.assertEqual(vol.backendjobid, 42)
        args, kwargs = mrapi().ModifyInstance.call_args
        self.assertEqual(kwargs["instance"], vm.backend_vm_id)
        self.assertEqual(kwargs["disks"][0], ("remove",
                                              vol.backend_volume_uuid, {}))
