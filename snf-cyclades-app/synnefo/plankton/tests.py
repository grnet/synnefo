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
import urllib

from mock import patch
from functools import wraps
from copy import deepcopy
from decimal import Decimal
from snf_django.utils.testing import BaseAPITest
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls

PLANKTON_URL = get_service_path(cyclades_services, 'image',
                                version='v1.0')
IMAGES_URL = join_urls(PLANKTON_URL, "images/")


def assert_backend_closed(func):
    @wraps(func)
    def wrapper(self, backend):
        result = func(self, backend)
        if backend.called is True:
            backend.return_value.close.assert_called_once_with()
        return result
    return wrapper


@patch("synnefo.plankton.backend.get_pithos_backend")
class PlanktonTest(BaseAPITest):
    def test_register_image(self, backend):
        required = {
            "HTTP_X_IMAGE_META_NAME": u"TestImage\u2602",
            "HTTP_X_IMAGE_META_LOCATION": "pithos://4321-4321/%E2%98%82/foo"}
        # Check valid name
        headers = deepcopy(required)
        headers.pop("HTTP_X_IMAGE_META_NAME")
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        self.assertTrue("name" in response.content)
        headers["HTTP_X_IMAGE_META_NAME"] = ""
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        self.assertTrue("name" in response.content)
        # Check valid location
        headers = deepcopy(required)
        headers.pop("HTTP_X_IMAGE_META_LOCATION")
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        self.assertTrue("location" in response.content)
        headers["HTTP_X_IMAGE_META_LOCATION"] = ""
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        self.assertTrue("location" in response.content)
        headers["HTTP_X_IMAGE_META_LOCATION"] = "pitho://4321-4321/images/foo"
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        self.assertTrue("location" in response.content)
        headers["HTTP_X_IMAGE_META_LOCATION"] = "pithos://4321-4321/foo"
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        self.assertTrue("location" in response.content)
        # ID not supported
        headers = deepcopy(required)
        headers["HTTP_X_IMAGE_META_ID"] = "1234"
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        headers = deepcopy(required)
        # ID not supported
        headers = deepcopy(required)
        headers["HTTP_X_IMAGE_META_LOLO"] = "1234"
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        headers = deepcopy(required)
        headers["HTTP_X_IMAGE_META_STORE"] = "pitho"
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        self.assertTrue("store " in response.content)
        headers = deepcopy(required)
        headers["HTTP_X_IMAGE_META_DISK_FORMAT"] = "diskdumpp"
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        self.assertTrue("disk format" in response.content)
        headers = deepcopy(required)
        headers["HTTP_X_IMAGE_META_CONTAINER_FORMAT"] = "baree"
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        self.assertTrue("container format" in response.content)

        backend().get_object_meta.return_value = {"uuid": "1234-1234-1234",
                                                  "bytes": 42,
                                                  "is_snapshot": True,
                                                  "hash": "unique_mapfile",
                                                  "is_snapshot": True,
                                                  "mapfile": "unique_mapfile"}
        headers = deepcopy(required)
        headers["HTTP_X_IMAGE_META_SIZE"] = "foo"
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        self.assertTrue("size" in response.content)
        headers["HTTP_X_IMAGE_META_SIZE"] = "43"
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        self.assertTrue("size" in response.content)

        # Unicode Error:
        headers["HTTP_X_IMAGE_META_NAME"] = "\xc2"
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)
        headers["HTTP_X_IMAGE_META_NAME"] = u"TestImage\u2602"

        headers["HTTP_X_IMAGE_META_SIZE"] = 42
        headers["HTTP_X_IMAGE_META_CHECKSUM"] = "wrong_checksum"
        response = self.post(IMAGES_URL, **headers)
        self.assertBadRequest(response)

        backend().get_object_by_uuid.return_value = (
            {"uuid": "1234-1234-1234",
             "bytes": 42,
             "mapfile": "unique_mapfile",
             "is_snapshot": True,
             "hash": "unique_mapfile",
             "version": 42,
             'version_timestamp': Decimal('1392487853.863673'),
             "plankton:name": u"TestImage\u2602",
             "plankton:container_format": "bare",
             "plankton:disk_format": "diskdump",
             "plankton:status": u"AVAILABLE"},
            {"read": []},
            u"4321-4321/\u2602/foo",
        )
        headers = deepcopy(required)
        response = self.post(IMAGES_URL, **headers)
        self.assertSuccess(response)
        self.assertEqual(response["x-image-meta-location"],
                         "pithos://4321-4321/%E2%98%82/foo")
        self.assertEqual(response["x-image-meta-id"], "1234-1234-1234")
        self.assertEqual(response["x-image-meta-status"], "AVAILABLE")
        self.assertEqual(response["x-image-meta-deleted-at"], "")
        self.assertEqual(response["x-image-meta-is-public"], "False")
        self.assertEqual(response["x-image-meta-owner"], "4321-4321")
        self.assertEqual(response["x-image-meta-size"], "42")
        self.assertEqual(response["x-image-meta-checksum"], "unique_mapfile")
        self.assertEqual(urllib.unquote(response["x-image-meta-name"]),
                         u"TestImage\u2602".encode("utf-8"))
        self.assertEqual(response["x-image-meta-container-format"], "bare")
        self.assertEqual(response["x-image-meta-disk-format"], "diskdump")
        self.assertEqual(response["x-image-meta-created-at"],
                         "2014-02-15 18:10:53")
        self.assertEqual(response["x-image-meta-updated-at"],
                         "2014-02-15 18:10:53")

        # Extra headers,properties
        backend().get_object_by_uuid.return_value = (
            {"uuid": "1234-1234-1234",
             "bytes": 42,
             "is_snapshot": True,
             "hash": "unique_mapfile",
             "mapfile": "unique_mapfile",
             "version": 42,
             'version_timestamp': Decimal('1392487853.863673'),
             "plankton:name": u"TestImage\u2602",
             "plankton:container_format": "bare",
             "plankton:disk_format": "diskdump",
             "plankton:status": u"AVAILABLE"},
            {"read": []},
            u"4321-4321/\u2602/foo",
        )
        headers = deepcopy(required)
        headers["HTTP_X_IMAGE_META_IS_PUBLIC"] = True
        headers["HTTP_X_IMAGE_META_PROPERTY_KEY1"] = "val1"
        headers["HTTP_X_IMAGE_META_PROPERTY_KEY2"] = u"\u2601"
        response = self.post(IMAGES_URL, **headers)
        name, args, kwargs = backend().update_object_meta.mock_calls[-1]
        metadata = args[5]
        self.assertEqual(metadata["plankton:property:key1"], "val1")
        self.assertEqual(metadata["plankton:property:key2"], u"\u2601")
        self.assertSuccess(response)

    def test_unregister_image(self, backend):
        backend().get_object_by_uuid.return_value = (
            {"uuid": "img_uuid",
             "bytes": 42,
             "plankton:name": "test"},
            {"read": []},
            "img_owner/images/foo"
        )
        response = self.delete(join_urls(IMAGES_URL, "img_uuid"))
        self.assertEqual(response.status_code, 204)
        backend().update_object_meta.assert_called_once_with(
            "user", "img_owner", "images", "foo", "plankton", {}, True)

    def test_users(self, backend):
        """Test adding/removing and replacing image members"""
        # Add user
        backend.reset_mock()
        backend().get_object_by_uuid.return_value = (
            {"uuid": "img_uuid",
             "bytes": 42,
             "plankton:name": "test"},
            {"read": []},
            "img_owner/images/foo")
        response = self.put(join_urls(IMAGES_URL, "img_uuid/members/user1"),
                            user="user1")
        self.assertSuccess(response)
        backend().update_object_permissions.assert_called_once_with(
            "user1", "img_owner", "images", "foo", {"read": ["user1"]})

        # Remove user
        backend().update_object_permissions.reset_mock()
        backend().get_object_by_uuid.return_value = (
            {"uuid": "img_uuid",
             "bytes": 42,
             "plankton:name": "test"},
            {"read": ["user1"]},
            "img_owner/images/foo")
        response = self.delete(join_urls(IMAGES_URL, "img_uuid/members/user1"),
                               user="user1")
        self.assertSuccess(response)
        backend().update_object_permissions.assert_called_once_with(
            "user1", "img_owner", "images", "foo", {"read": []})

        # Update users
        backend().get_object_by_uuid.return_value = (
            {"uuid": "img_uuid",
             "bytes": 42,
             "plankton:name": "test"},
            {"read": ["user1", "user2", "user3"]},
            "img_owner/images/foo")
        backend().update_object_permissions.reset_mock()
        response = self.put(join_urls(IMAGES_URL, "img_uuid/members"),
                            params=json.dumps({"memberships":
                                               [{"member_id": "foo1"},
                                                {"member_id": "foo2"}]}),
                            ctype="json",
                            user="user1")
        self.assertSuccess(response)
        backend().update_object_permissions.assert_called_once_with(
            "user1", "img_owner", "images", "foo", {"read": ["foo1", "foo2"]})

        # List users
        backend().get_object_by_uuid.return_value = (
            {"uuid": "img_uuid",
             "bytes": 42,
             "plankton:name": "test"},
            {"read": ["user1", "user2", "user3"]},
            "img_owner/images/foo",
        )
        response = self.get(join_urls(IMAGES_URL, "img_uuid/members"))
        self.assertSuccess(response)
        res_members = [{"member_id": m, "can_share": False}
                       for m in ["user1", "user2", "user3"]]
        self.assertEqual(json.loads(response.content)["members"], res_members)

    def test_metadata(self, backend):
        backend().get_object_by_uuid.return_value = (
            {"uuid": "img_uuid",
             "bytes": 42,
             "is_snapshot": True,
             "hash": "unique_mapfile",
             "mapfile": "unique_mapfile",
             "version": 42,
             'version_timestamp': Decimal('1392487853.863673'),
             "plankton:name": u"TestImage\u2602",
             "plankton:container_format": "bare",
             "plankton:disk_format": "diskdump",
             "plankton:status": u"AVAILABLE"},
            {"read": ["*", "user1"]},
            "img_owner/images/foo/foo1/foo2/foo3",
        )
        response = self.head(join_urls(IMAGES_URL, "img_uuid2"))
        self.assertSuccess(response)
        self.assertEqual(response["x-image-meta-location"],
                         "pithos://img_owner/images/foo/foo1/foo2/foo3")
        self.assertEqual(response["x-image-meta-id"], "img_uuid")
        self.assertEqual(response["x-image-meta-status"], "AVAILABLE")
        self.assertEqual(response["x-image-meta-deleted-at"], "")
        self.assertEqual(response["x-image-meta-is-public"], "True")
        self.assertEqual(response["x-image-meta-owner"], "img_owner")
        self.assertEqual(response["x-image-meta-size"], "42")
        self.assertEqual(response["x-image-meta-checksum"], "unique_mapfile")
        self.assertEqual(urllib.unquote(response["x-image-meta-name"]),
                         u"TestImage\u2602".encode("utf-8"))
        self.assertEqual(response["x-image-meta-container-format"], "bare")
        self.assertEqual(response["x-image-meta-disk-format"], "diskdump")
        self.assertEqual(response["x-image-meta-created-at"],
                         "2014-02-15 18:10:53")
        self.assertEqual(response["x-image-meta-updated-at"],
                         "2014-02-15 18:10:53")
        response = self.head(join_urls(IMAGES_URL, "img_uuid2"))

        headers = {"HTTP_X_IMAGE_META_IS_PUBLIC": False,
                   "HTTP_X_IMAGE_META_PROPERTY_KEY1": "Val1"}
        response = self.put(join_urls(IMAGES_URL, "img_uuid"), **headers)
        self.assertSuccess(response)
        backend().update_object_permissions.assert_called_once_with(
            "user", "img_owner", "images", "foo/foo1/foo2/foo3",
            {"read": ["user1"]})

    def test_catch_wrong_api_paths(self, *args):
        response = self.get(join_urls(PLANKTON_URL, 'nonexistent'))
        self.assertEqual(response.status_code, 400)
        try:
            json.loads(response.content)
        except ValueError:
            self.assertTrue(False)

    def test_list_images_filters_error_1(self, backend):
        response = self.get(join_urls(IMAGES_URL, "?size_max="))
        self.assertBadRequest(response)
