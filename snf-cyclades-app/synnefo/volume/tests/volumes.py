from snf_django.utils.testing import BaseAPITest
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
        self.assertEqual(disk_info["volume_name"], vol.backend_volume_uuid)
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

        svol.status = "AVAILABLE"
        svol.save()
        mrapi().ModifyInstance.return_value = 42
        vol = volumes.create(source_volume_id=svol.id, **self.kwargs)

        self.assertEqual(vol.size, self.size)
        self.assertEqual(vol.userid, self.userid)
        self.assertEqual(vol.name, None)
        self.assertEqual(vol.description, None)
        self.assertEqual(vol.source, "volume:%s" % svol.id)
        self.assertEqual(vol.origin, svol.backend_volume_uuid)

        name, args, kwargs = mrapi().ModifyInstance.mock_calls[0]
        self.assertEqual(kwargs["instance"], self.vm.backend_vm_id)
        disk_info = kwargs["disks"][0][2]
        self.assertEqual(disk_info["size"], self.size << 10)
        self.assertEqual(disk_info["name"], vol.backend_volume_uuid)
        self.assertEqual(disk_info["volume_name"], vol.backend_volume_uuid)
        self.assertEqual(disk_info["origin"], svol.backend_volume_uuid)

    @patch("synnefo.plankton.backend.ImageBackend")
    def test_create_from_snapshot(self, mimage, mrapi):
        # Wrong source
        mimage().get_snapshot.side_effect = faults.ItemNotFound
        self.assertRaises(faults.BadRequest,
                          volumes.create,
                          source_snapshot_id=421,
                          **self.kwargs)

        mimage().get_snapshot.side_effect = None
        mimage().get_snapshot.return_value = {
            'location': 'pithos://foo',
            'mapfile': 'snf-snapshot-43',
            'id': 12,
            'name': "test_image",
            'size': 1242,
            'disk_format': 'diskdump',
            'properties': {'source_volume': 42}}

        mrapi().ModifyInstance.return_value = 42
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
        self.assertEqual(disk_info["volume_name"], vol.backend_volume_uuid)
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
        volumes.delete(vol)
        self.assertEqual(vol.backendjobid, 42)
        args, kwargs = mrapi().ModifyInstance.call_args
        self.assertEqual(kwargs["instance"], vm.backend_vm_id)
        self.assertEqual(kwargs["disks"][0], ("remove",
                                              vol.backend_volume_uuid, {}))
