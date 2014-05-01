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

from snf_django.utils.testing import BaseAPITest
from synnefo.db.models_factory import VolumeTypeFactory
from synnefo.lib.services import get_service_path
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib import join_urls

VOLUME_URL = get_service_path(cyclades_services, 'volume',
                              version='v2.0')
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
