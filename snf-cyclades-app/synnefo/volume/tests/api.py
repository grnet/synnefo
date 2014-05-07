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

from mock import patch
from snf_django.utils.testing import BaseAPITest
from synnefo.db.models_factory import VolumeFactory, VolumeTypeFactory
from synnefo.lib.services import get_service_path
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib import join_urls

VOLUME_URL = get_service_path(cyclades_services, 'volume',
                              version='v2.0')
VOLUMES_URL = join_urls(VOLUME_URL, "volumes")


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
