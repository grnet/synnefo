# Copyright 2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import json

from mock import patch
from functools import wraps
from copy import deepcopy
from snf_django.utils.testing import BaseAPITest


FILTERS = ('name', 'container_format', 'disk_format', 'status', 'size_min',
           'size_max')
PARAMS = ('sort_key', 'sort_dir')
SORT_KEY_OPTIONS = ('id', 'name', 'status', 'size', 'disk_format',
                    'container_format', 'created_at', 'updated_at')
SORT_DIR_OPTIONS = ('asc', 'desc')
LIST_FIELDS = ('status', 'name', 'disk_format', 'container_format', 'size',
               'id')
DETAIL_FIELDS = ('name', 'disk_format', 'container_format', 'size', 'checksum',
                 'location', 'created_at', 'updated_at', 'deleted_at',
                 'status', 'is_public', 'owner', 'properties', 'id')
ADD_FIELDS = ('name', 'id', 'store', 'disk_format', 'container_format', 'size',
              'checksum', 'is_public', 'owner', 'properties', 'location')
UPDATE_FIELDS = ('name', 'disk_format', 'container_format', 'is_public',
                 'owner', 'properties', 'status')


DummyImages = {
 '0786a349-9725-48ec-8b86-8598eefc4043':
 {'checksum': u'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  u'container_format': u'bare',
  'created_at': '2012-12-04 09:50:20',
  'deleted_at': '',
  u'disk_format': u'diskdump',
  'id': u'0786a349-9725-48ec-8b86-8598eefc4043',
  'is_public': True,
  'location': u'pithos://foo@example.com/container/foo3',
  u'name': u'dummyname',
  'owner': u'foo@example.com',
  'properties': {},
  'size': 500L,
  u'status': u'available',
  'store': 'pithos',
  'updated_at': '2012-12-04 09:50:54'},

 'd8aa85b8-410b-4550-953d-6797572534e6':
 {'checksum': u'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  u'container_format': u'bare',
  'created_at': '2012-11-26 11:56:42',
  'deleted_at': '',
  u'disk_format': u'diskdump',
  'id': u'd8aa85b8-410b-4550-953d-6797572534e6',
  'is_public': False,
  'location': u'pithos://foo@example.com/container/private',
  u'name': u'dummyname2',
  'owner': u'foo@example.com',
  'properties': {},
  'size': 10000L,
  u'status': u'available',
  'store': 'pithos',
  'updated_at': '2012-11-26 11:57:09'},

 '264fb9ac-2458-421c-b460-6a765a92825c':
 {'checksum': u'0c6d0586744781218672fff2d7ed94cc32efb02a6a8eb589a0628f0e22bd5a7f',
  u'container_format': u'bare',
  'created_at': '2012-11-26 11:52:54',
  'deleted_at': '',
  u'disk_format': u'diskdump',
  'id': u'264fb9ac-2458-421c-b460-6a765a92825c',
  'is_public': True,
  'location': u'pithos://foo@example.com/container/baz.diskdump',
  u'name': u'"dummyname3"',
  'owner': u'foo@example.com',
  'properties': {u'description': u'Debian Squeeze Base System',
                 u'gui': u'No GUI',
                 u'kernel': u'2.6.32',
                 u'os': u'debian',
                 u'osfamily': u'linux',
                 u'root_partition': u'1',
                 u'size': u'451',
                 u'sortorder': u'1',
                 u'users': u'root'},
  'size': 473772032L,
  u'status': u'available',
  'store': 'pithos',
  'updated_at': '2012-11-26 11:55:40'}}


def assert_backend_closed(func):
    @wraps(func)
    def wrapper(self, backend):
        result = func(self, backend)
        if backend.called is True:
            backend.return_value.close.assert_called_once_with()
        return result
    return wrapper


@patch("synnefo.plankton.backend.ImageBackend")
class PlanktonTest(BaseAPITest):
    @assert_backend_closed
    def test_list_images(self, backend):
        backend.return_value.list_images.return_value =\
                deepcopy(DummyImages).values()
        response = self.get("/plankton/images/")
        self.assertSuccess(response)
        images = json.loads(response.content)
        for api_image in images:
            id = api_image['id']
            pithos_image = dict([(key, val)\
                                for key, val in DummyImages[id].items()\
                                if key in LIST_FIELDS])
            self.assertEqual(api_image, pithos_image)
        backend.return_value\
                .list_images.assert_called_once_with({}, {'sort_key': 'created_at',
                                                   'sort_dir': 'desc'})

    @assert_backend_closed
    def test_list_images_detail(self, backend):
        backend.return_value.list_images.return_value =\
                deepcopy(DummyImages).values()
        response = self.get("/plankton/images/detail")
        self.assertSuccess(response)
        images = json.loads(response.content)
        for api_image in images:
            id = api_image['id']
            pithos_image = dict([(key, val)\
                                for key, val in DummyImages[id].items()\
                                if key in DETAIL_FIELDS])
            self.assertEqual(api_image, pithos_image)
        backend.return_value\
                .list_images.assert_called_once_with({}, {'sort_key': 'created_at',
                                                   'sort_dir': 'desc'})

    @assert_backend_closed
    def test_list_images_filters(self, backend):
        backend.return_value.list_images.return_value =\
                deepcopy(DummyImages).values()
        response = self.get("/plankton/images/?size_max=1000")
        self.assertSuccess(response)
        backend.return_value\
                .list_images.assert_called_once_with({'size_max': 1000},
                                                     {'sort_key': 'created_at',
                                                     'sort_dir': 'desc'})

    @assert_backend_closed
    def test_list_images_filters_error_1(self, backend):
        response = self.get("/plankton/images/?size_max=")
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_list_images_filters_error_2(self, backend):
        response = self.get("/plankton/images/?size_min=foo")
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_update_image(self, backend):
        db_image = DummyImages.values()[0]
        response = self.put("/plankton/images/%s" % db_image['id'],
                            json.dumps({}),
                            'json', HTTP_X_IMAGE_META_OWNER='user2')
        self.assertSuccess(response)
        backend.return_value.update_metadata.assert_called_once_with(db_image['id'],
                                                                     {"owner": "user2"})

    @assert_backend_closed
    def test_add_image_member(self, backend):
        image_id = DummyImages.values()[0]['id']
        response = self.put("/plankton/images/%s/members/user3" % image_id,
                            json.dumps({}), 'json')
        self.assertSuccess(response)
        backend.return_value.add_user.assert_called_once_with(image_id,
                                                             'user3')

    @assert_backend_closed
    def test_remove_image_member(self, backend):
        image_id = DummyImages.values()[0]['id']
        response = self.delete("/plankton/images/%s/members/user3" % image_id)
        self.assertSuccess(response)
        backend.return_value.remove_user.assert_called_once_with(image_id,
                                                                'user3')

    @assert_backend_closed
    def test_add_image(self, backend):
        response = self.post("/plankton/images/",
                             json.dumps({}),
                             'json',
                             HTTP_X_IMAGE_META_NAME='dummy_name',
                             HTTP_X_IMAGE_META_OWNER='dummy_owner',
                             HTTP_X_IMAGE_META_LOCATION='dummy_location')
        self.assertSuccess(response)
        backend.return_value.register.assert_called_once_with('dummy_name',
                                                              'dummy_location',
                                                      {'owner': 'dummy_owner'})

    @assert_backend_closed
    def test_get_image(self, backend):
        response = self.get("/plankton/images/123")
        self.assertEqual(response.status_code, 501)

    @assert_backend_closed
    def test_delete_image(self, backend):
        response = self.delete("/plankton/images/123")
        self.assertEqual(response.status_code, 204)
        backend.return_value.unregister.assert_called_once_with('123')
        backend.return_value._delete.assert_not_called()
