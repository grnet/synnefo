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
