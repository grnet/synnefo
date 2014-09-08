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

import json

from mock import patch, Mock
from snf_django.utils.testing import BaseAPITest, mocked_quotaholder
from synnefo.db.models_factory import (VolumeFactory, VolumeTypeFactory,
                                       VirtualMachineFactory)
from synnefo.lib.services import get_service_path
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib import join_urls
from copy import deepcopy

VOLUME_URL = get_service_path(cyclades_services, 'volume',
                              version='v2.0')
VOLUMES_URL = join_urls(VOLUME_URL, "volumes")


@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class VolumeAPITest(BaseAPITest):
    def test_create_volume(self, mrapi):
        vm = VirtualMachineFactory(
            operstate="ACTIVE",
            flavor__volume_type__disk_template="ext_vlmc")
        user = vm.userid
        _data = {"display_name": "test_vol",
                 "size": 2,
                 "server_id": vm.id}

        # Test Success
        mrapi().ModifyInstance.return_value = 42
        with mocked_quotaholder():
            r = self.post(VOLUMES_URL, user,
                          json.dumps({"volume": _data}), "json")
        self.assertSuccess(r)

        # Test create without size, name and server
        for attr in ["display_name", "size", "server_id"]:
            data = deepcopy(_data)
            del data["size"]
            with mocked_quotaholder():
                r = self.post(VOLUMES_URL, user,
                              json.dumps({"volume": data}), "json")
            self.assertBadRequest(r)

        # Test invalid size
        data = deepcopy(_data)
        data["size"] = -2
        with mocked_quotaholder():
            r = self.post(VOLUMES_URL, user,
                          json.dumps({"volume": data}), "json")
        self.assertBadRequest(r)

        # Test deleted server or invalid state
        data = deepcopy(_data)
        vm.deleted = True
        vm.save()
        with mocked_quotaholder():
            r = self.post(VOLUMES_URL, user,
                          json.dumps({"volume": data}), "json")
        self.assertBadRequest(r)

        vm.deleted = False
        vm.operstate = "ERROR"
        vm.save()
        with mocked_quotaholder():
            r = self.post(VOLUMES_URL, user,
                          json.dumps({"volume": data}), "json")
        self.assertBadRequest(r)
        vm.operstate = "ACTIVE"
        vm.save()

        # Test volume type different from VM's flavor or invalid vype
        data = deepcopy(_data)
        for disk_type in ["file", "plain", "drbd", "rbd"]:
            vtype = VolumeTypeFactory(disk_template=disk_type)
            data["volume_type"] = vtype.id
            with mocked_quotaholder():
                r = self.post(VOLUMES_URL, user,
                              json.dumps({"volume": data}), "json")
            self.assertBadRequest(r)
        for vtype in [434132421243, "foo"]:
            data["volume_type"] = vtype
            with mocked_quotaholder():
                r = self.post(VOLUMES_URL, user,
                              json.dumps({"volume": data}), "json")
            self.assertBadRequest(r)

        # Test source for invalid disk template
        for disk_type in ["file", "plain", "drbd", "rbd"]:
            temp_vm = VirtualMachineFactory(
                operstate="ACTIVE",
                flavor__volume_type__disk_template=disk_type)
            for attr in ["snapshot_id", "imageRef"]:
                data = deepcopy(_data)
                data["server_id"] = temp_vm.id
                data[attr] = "3214231-413242134123-431242"
                with mocked_quotaholder():
                    r = self.post(VOLUMES_URL, user,
                                  json.dumps({"volume": data}), "json")
                self.assertBadRequest(r)

        # Test snapshot and image together
        data = deepcopy(_data)
        data["snapshot_id"] = "3214231-413242134123-431242"
        data["imageRef"] = "3214231-413242134123-431242"
        with mocked_quotaholder():
            r = self.post(VOLUMES_URL, user,
                          json.dumps({"volume": data}), "json")
        self.assertBadRequest(r)

        # Test with Snapshot source

        # Test unknwon snapshot
        data = deepcopy(_data)
        data["snapshot_id"] = "94321904321-432142134214-23142314"
        with mocked_quotaholder():
            r = self.post(VOLUMES_URL, user,
                          json.dumps({"volume": data}), "json")
        self.assertBadRequest(r)

        vm.task = None
        vm.action = None
        vm.save()
        # Test success
        snapshot = Mock()
        snapshot.return_value = {'location': 'pithos://foo',
                                 'mapfile': '1234',
                                 'id': 1,
                                 'name': 'test_image',
                                 'size': 1024,
                                 'is_snapshot': True,
                                 'is_public': True,
                                 'version': 42,
                                 'owner': 'user',
                                 'status': 'AVAILABLE',
                                 'disk_format': 'diskdump'}
        data["snapshot_id"] = 1
        with patch("synnefo.volume.util.get_snapshot", snapshot):
            with mocked_quotaholder():
                r = self.post(VOLUMES_URL, user,
                              json.dumps({"volume": data}), "json")
        self.assertSuccess(r)

        # Test with Snapshot source

        # Test unknwon snapshot
        data = deepcopy(_data)
        data["imageRef"] = "94321904321-432142134214-23142314"
        with mocked_quotaholder():
            r = self.post(VOLUMES_URL, user,
                          json.dumps({"volume": data}), "json")
        self.assertBadRequest(r)

        vm.task = None
        vm.action = None
        vm.save()
        data["server_id"] = vm.id
        # Test success
        image = Mock()
        image.return_value = {'location': 'pithos://foo',
                              'mapfile': '1234',
                              'id': 2,
                              'name': 'test_image',
                              'size': 1024,
                              'is_snapshot': False,
                              'is_image': False,
                              'is_public': True,
                              'owner': 'user',
                              'version': 42,
                              'status': 'AVAILABLE',
                              'disk_format': 'diskdump'}
        data["imageRef"] = 2
        with patch("synnefo.api.util.get_image", image):
            with mocked_quotaholder():
                r = self.post(VOLUMES_URL, user,
                              json.dumps({"volume": data}), "json")
        self.assertSuccess(r)

    def test_rud(self, mrapi):
        vol = VolumeFactory(status="IN_USE")
        user = vol.userid
        # READ
        r = self.get(join_urls(VOLUMES_URL, "detail"), user)
        api_vols = json.loads(r.content)["volumes"]
        self.assertEqual(len(api_vols), 1)
        api_vol = api_vols[0]
        self.assertEqual(api_vol["id"], str(vol.id))
        self.assertEqual(api_vol["display_name"], vol.name)
        self.assertEqual(api_vol["display_description"], vol.description)

        volume_url = join_urls(VOLUMES_URL, str(vol.id))
        r = self.get(volume_url, user)
        self.assertSuccess(r)

        # UPDATE
        data = {
            "volume": {
                "display_name": "lolo",
                "display_description": "lala"
            }
        }

        r = self.put(volume_url, user, json.dumps(data), "json")
        self.assertSuccess(r)
        api_vol = json.loads(r.content)["volume"]
        self.assertEqual(api_vol["display_name"], "lolo")
        self.assertEqual(api_vol["display_description"], "lala")

        # DELETE
        mrapi().ModifyInstance.return_value = 42
        r = self.delete(volume_url, user)
        self.assertSuccess(r)


class VolumeMetadataAPITest(BaseAPITest):
    def test_volume_metadata(self):
        vol = VolumeFactory()
        volume_metadata_url = join_urls(join_urls(VOLUMES_URL, str(vol.id)),
                                        "metadata")
        # Empty metadata
        response = self.get(volume_metadata_url, vol.userid)
        self.assertSuccess(response)
        metadata = json.loads(response.content)["metadata"]
        self.assertEqual(metadata, {})

        # Create metadata items
        meta1 = {"metadata": {"key1": "val1", "\u2601": "\u2602"}}
        response = self.post(volume_metadata_url, vol.userid,
                             json.dumps(meta1), "json")
        self.assertSuccess(response)
        response = self.get(volume_metadata_url, vol.userid)
        self.assertSuccess(response)
        metadata = json.loads(response.content)
        self.assertEqual(metadata, meta1)

        # Update existing metadata and add new
        meta2 = {"metadata": {"\u2601": "unicode_val_2", "key3": "val3"}}
        meta_db = {"metadata": {"key1": "val1",
                                "\u2601": "unicode_val_2",
                                "key3": "val3"}}
        response = self.post(volume_metadata_url, vol.userid,
                             json.dumps(meta2), "json")
        self.assertSuccess(response)
        metadata = json.loads(response.content)
        self.assertEqual(metadata, meta_db)
        response = self.get(volume_metadata_url, vol.userid)
        self.assertSuccess(response)
        metadata = json.loads(response.content)
        self.assertEqual(metadata, meta_db)
        # Replace all metadata
        meta3 = {"metadata": {"key4": "val4"}}
        response = self.put(volume_metadata_url, vol.userid,
                            json.dumps(meta3), "json")
        self.assertSuccess(response)
        response = self.get(volume_metadata_url, vol.userid)
        self.assertSuccess(response)
        metadata = json.loads(response.content)
        self.assertEqual(metadata, meta3)

        # Delete metadata key
        response = self.delete(join_urls(volume_metadata_url, "key4"),
                               vol.userid)
        self.assertSuccess(response)
        response = self.get(volume_metadata_url, vol.userid)
        self.assertSuccess(response)
        metadata = json.loads(response.content)["metadata"]
        self.assertEqual(metadata, {})


VOLUME_TYPES_URL = join_urls(VOLUME_URL, "types/")


class VolumeTypeAPITest(BaseAPITest):
    def test_list(self):
        VolumeTypeFactory(disk_template="drbd", name="drbd1")
        VolumeTypeFactory(disk_template="file", name="file1")
        VolumeTypeFactory(disk_template="plain", name="deleted",
                          deleted=True)
        response = self.get(VOLUME_TYPES_URL)
        self.assertSuccess(response)
        api_vtypes = json.loads(response.content)["volume_types"]
        self.assertEqual(len(api_vtypes), 2)
        self.assertEqual(api_vtypes[0]["SNF:disk_template"], "drbd")
        self.assertEqual(api_vtypes[0]["name"], "drbd1")
        self.assertEqual(api_vtypes[1]["SNF:disk_template"], "file")
        self.assertEqual(api_vtypes[1]["name"], "file1")

    def test_get(self):
        vtype1 = VolumeTypeFactory(disk_template="drbd", name="drbd1")
        vtype2 = VolumeTypeFactory(disk_template="drbd", name="drbd2")
        response = self.get(join_urls(VOLUME_TYPES_URL, str(vtype1.id)))
        self.assertSuccess(response)
        api_vtype = json.loads(response.content)["volume_type"]
        self.assertEqual(api_vtype["SNF:disk_template"], "drbd")
        self.assertEqual(api_vtype["name"], "drbd1")
        self.assertEqual(api_vtype["deleted"], False)

        vtype2.deleted = True
        vtype2.save()
        response = self.get(join_urls(VOLUME_TYPES_URL, str(vtype2.id)))
        self.assertSuccess(response)
        api_vtype = json.loads(response.content)["volume_type"]
        self.assertEqual(api_vtype["SNF:disk_template"], "drbd")
        self.assertEqual(api_vtype["name"], "drbd1")
        self.assertEqual(api_vtype["deleted"], True)


SNAPSHOTS_URL = join_urls(VOLUME_URL, "snapshots")


@patch("synnefo.plankton.backend.PlanktonBackend")
class SnapshotMetadataAPITest(BaseAPITest):
    def test_snapshot_metadata(self, mimage):
        snap_id = u"1234-4321-1234"
        snap_meta_url = join_urls(join_urls(SNAPSHOTS_URL, snap_id),
                                  "metadata")
        mimage().__enter__().get_snapshot.return_value = {"properties": {}}

        # Empty metadata
        response = self.get(snap_meta_url, "user")
        self.assertSuccess(response)
        metadata = json.loads(response.content)["metadata"]
        self.assertEqual(metadata, {})

        # Create metadata items
        properties = {"key1": "val1", "\u2601": "\u2602"}
        meta = {"metadata": properties}
        mimage().__enter__().get_snapshot.return_value = \
            {"properties": properties}
        response = self.post(snap_meta_url, "user",
                             json.dumps(meta), "json")
        self.assertSuccess(response)
        mimage().__enter__().update_properties.assert_called_with(
            snap_id, properties, replace=False)
        response = self.get(snap_meta_url, "user")
        self.assertSuccess(response)
        metadata = json.loads(response.content)
        self.assertEqual(metadata, meta)

        # Update existing metadata and add new
        properties = {"\u2601": "unicode_val_2", "key3": "val3"}
        db_properties = {"key1": "val1",
                         "\u2601": "unicode_val_2",
                         "key3": "val3"}

        meta = {"metadata": properties}
        meta_db = {"metadata": {"key1": "val1",
                                "\u2601": "unicode_val_2",
                                "key3": "val3"}}
        mimage().__enter__().get_snapshot.return_value = \
            {"properties": db_properties}
        response = self.post(snap_meta_url, "user",
                             json.dumps(meta), "json")
        self.assertSuccess(response)
        mimage().__enter__().update_properties.assert_called_with(
            snap_id, properties, replace=False)
        metadata = json.loads(response.content)
        self.assertEqual(metadata, meta_db)
        response = self.get(snap_meta_url, "user")
        self.assertSuccess(response)
        metadata = json.loads(response.content)
        self.assertEqual(metadata, meta_db)

        properties = {"key4": "val4"}
        meta = {"metadata": properties}
        mimage().__enter__().get_snapshot.return_value = \
            {"properties": properties}
        # Replace all metadata
        response = self.put(snap_meta_url, "user",
                            json.dumps(meta), "json")
        mimage().__enter__().update_properties.assert_called_with(
            snap_id, properties, replace=True)
        self.assertSuccess(response)
        response = self.get(snap_meta_url, "user")
        self.assertSuccess(response)
        metadata = json.loads(response.content)
        self.assertEqual(metadata, meta)

        # Delete metadata key
        response = self.delete(join_urls(snap_meta_url, "key4"),
                               "user")
        self.assertSuccess(response)
        mimage().__enter__().remove_property.assert_called_with(
            snap_id, "key4")
