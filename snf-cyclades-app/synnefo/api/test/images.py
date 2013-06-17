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

from snf_django.lib.api import faults
from snf_django.utils.testing import BaseAPITest
from synnefo.lib.services import get_service_path
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib import join_urls

from mock import patch
from functools import wraps


def assert_backend_closed(func):
    """Decorator for ensuring that ImageBackend is returned to pool."""
    @wraps(func)
    def wrapper(self, backend):
        result = func(self, backend)
        if backend.called is True:
            backend.return_value.close.asssert_called
        return result
    return wrapper


class ComputeAPITest(BaseAPITest):
    def setUp(self, *args, **kwargs):
        super(ComputeAPITest, self).setUp(*args, **kwargs)
        self.compute_path = get_service_path(cyclades_services, 'compute',
                                             version='v2.0')
    def myget(self, path, *args, **kwargs):
        path = join_urls(self.compute_path, path)
        return self.get(path, *args, **kwargs)

    def myput(self, path, *args, **kwargs):
        path = join_urls(self.compute_path, path)
        return self.put(path, *args, **kwargs)

    def mypost(self, path, *args, **kwargs):
        path = join_urls(self.compute_path, path)
        return self.post(path, *args, **kwargs)

    def mydelete(self, path, *args, **kwargs):
        path = join_urls(self.compute_path, path)
        return self.delete(path, *args, **kwargs)


@patch('synnefo.plankton.backend.ImageBackend')
class ImageAPITest(ComputeAPITest):
    @assert_backend_closed
    def test_create_image(self, mimage):
        """Test that create image is not implemented"""
        response = self.mypost('images/', 'user', json.dumps(''), 'json')
        self.assertEqual(response.status_code, 501)

    @assert_backend_closed
    def test_list_images(self, mimage):
        """Test that expected list of images is returned"""
        images = [{'id': 1, 'name': 'image-1'},
                  {'id': 2, 'name': 'image-2'},
                  {'id': 3, 'name': 'image-3'}]
        mimage().list_images.return_value = images
        response = self.myget('images', 'user')
        self.assertSuccess(response)
        api_images = json.loads(response.content)['images']
        self.assertEqual(images, api_images)

    @assert_backend_closed
    def test_list_images_detail(self, mimage):
        images = [{'id': 1,
                   'name': 'image-1',
                   'status':'available',
                   'created_at': '2012-11-26 11:52:54',
                   'updated_at': '2012-12-26 11:52:54',
                   'owner': 'user1',
                   'deleted_at': '',
                   'properties': {'foo':'bar'}},
                  {'id': 2,
                   'name': 'image-2',
                   'status': 'deleted',
                   'created_at': '2012-11-26 11:52:54',
                   'updated_at': '2012-12-26 11:52:54',
                   'owner': 'user1',
                   'deleted_at': '2012-12-27 11:52:54',
                   'properties': ''},
                  {'id': 3,
                   'name': 'image-3',
                   'status': 'available',
                   'created_at': '2012-11-26 11:52:54',
                   'deleted_at': '',
                   'updated_at': '2012-12-26 11:52:54',
                   'owner': 'user1',
                   'properties': ''}]
        result_images = [
                  {'id': 1,
                   'name': 'image-1',
                   'status':'ACTIVE',
                   'progress': 100,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00',
                   'user_id': 'user1',
                   'tenant_id': 'user1',
                   'metadata': {'foo':'bar'}},
                  {'id': 2,
                   'name': 'image-2',
                   'status': 'DELETED',
                   'progress': 0,
                   'user_id': 'user1',
                   'tenant_id': 'user1',
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00',
                   'metadata': {}},
                  {'id': 3,
                   'name': 'image-3',
                   'status': 'ACTIVE',
                   'progress': 100,
                   'user_id': 'user1',
                   'tenant_id': 'user1',
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00',
                   'metadata': {}}]
        mimage().list_images.return_value = images
        response = self.myget('images/detail', 'user')
        self.assertSuccess(response)
        api_images = json.loads(response.content)['images']
        self.assertEqual(len(result_images), len(api_images))
        map(lambda image: image.pop("links"), api_images)
        self.assertEqual(result_images, api_images)

    @assert_backend_closed
    def test_list_images_detail_since(self, mimage):
        from datetime import datetime, timedelta
        from time import sleep
        old_time = datetime.now()
        new_time = old_time + timedelta(seconds=0.1)
        sleep(0.1)
        images = [
                  {'id': 1,
                   'name': 'image-1',
                   'status':'available',
                   'progress': 100,
                   'created_at': old_time.isoformat(),
                   'deleted_at': '',
                   'updated_at': old_time.isoformat(),
                   'owner': 'user1',
                   'properties': ''},
                  {'id': 2,
                   'name': 'image-2',
                   'status': 'deleted',
                   'progress': 0,
                   'owner': 'user2',
                   'created_at': new_time.isoformat(),
                   'updated_at': new_time.isoformat(),
                   'deleted_at': new_time.isoformat(),
                   'properties': ''}]
        mimage().list_images.return_value = images
        response =\
            self.myget('images/detail?changes-since=%sUTC' % new_time)
        self.assertSuccess(response)
        api_images = json.loads(response.content)['images']
        self.assertEqual(1, len(api_images))

    @assert_backend_closed
    def test_get_image_details(self, mimage):
        image = {'id': 42,
                 'name': 'image-1',
                 'status': 'available',
                 'created_at': '2012-11-26 11:52:54',
                 'updated_at': '2012-12-26 11:52:54',
                 'deleted_at': '',
                 'owner': 'user1',
                 'properties': {'foo': 'bar'}}
        result_image = \
                  {'id': 42,
                   'name': 'image-1',
                   'status': 'ACTIVE',
                   'progress': 100,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00',
                   'user_id': 'user1',
                   'tenant_id': 'user1',
                   'metadata': {'foo': 'bar'}}
        mimage.return_value.get_image.return_value = image
        response = self.myget('images/42', 'user')
        self.assertSuccess(response)
        api_image = json.loads(response.content)['image']
        api_image.pop("links")
        self.assertEqual(api_image, result_image)

    @assert_backend_closed
    def test_invalid_image(self, mimage):
        mimage.return_value.get_image.side_effect = faults.ItemNotFound('Image not found')
        response = self.myget('images/42', 'user')
        self.assertItemNotFound(response)

    @assert_backend_closed
    def test_delete_image(self, mimage):
        response = self.mydelete("images/42", "user")
        self.assertEqual(response.status_code, 204)
        mimage.return_value.unregister.assert_called_once_with('42')
        mimage.return_value._delete.assert_not_called('42')

    @assert_backend_closed
    def test_catch_wrong_api_paths(self, *args):
        response = self.myget('nonexistent')
        self.assertEqual(response.status_code, 400)
        try:
            error = json.loads(response.content)
        except ValueError:
            self.assertTrue(False)

    @assert_backend_closed
    def test_method_not_allowed(self, *args):
        # /images/ allows only POST, GET
        response = self.myput('images', '', '')
        self.assertMethodNotAllowed(response)
        response = self.mydelete('images')
        self.assertMethodNotAllowed(response)

        # /images/<imgid>/ allows only GET, DELETE
        response = self.mypost("images/42")
        self.assertMethodNotAllowed(response)
        response = self.myput('images/42', '', '')
        self.assertMethodNotAllowed(response)

        # /images/<imgid>/metadata/ allows only POST, GET
        response = self.myput('images/42/metadata', '', '')
        self.assertMethodNotAllowed(response)
        response = self.mydelete('images/42/metadata')
        self.assertMethodNotAllowed(response)

        # /images/<imgid>/metadata/ allows only POST, GET
        response = self.myput('images/42/metadata', '', '')
        self.assertMethodNotAllowed(response)
        response = self.mydelete('images/42/metadata')
        self.assertMethodNotAllowed(response)

        # /images/<imgid>/metadata/<key> allows only PUT, GET, DELETE
        response = self.mypost('images/42/metadata/foo')
        self.assertMethodNotAllowed(response)


@patch('synnefo.plankton.backend.ImageBackend')
class ImageMetadataAPITest(ComputeAPITest):
    def setUp(self):
        self.image = {'id': 42,
                 'name': 'image-1',
                 'status': 'available',
                 'created_at': '2012-11-26 11:52:54',
                 'updated_at': '2012-12-26 11:52:54',
                 'deleted_at': '',
                 'properties': {'foo': 'bar', 'foo2': 'bar2'}}
        self.result_image = \
                  {'id': 42,
                   'name': 'image-1',
                   'status': 'ACTIVE',
                   'progress': 100,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00',
                   'metadata': {'foo': 'bar'}}
        super(ImageMetadataAPITest, self).setUp()

    @assert_backend_closed
    def test_list_metadata(self, backend):
        backend.return_value.get_image.return_value = self.image
        response = self.myget('images/42/metadata', 'user')
        self.assertSuccess(response)
        meta = json.loads(response.content)['metadata']
        self.assertEqual(meta, self.image['properties'])

    @assert_backend_closed
    def test_get_metadata(self, backend):
        backend.return_value.get_image.return_value = self.image
        response = self.myget('images/42/metadata/foo', 'user')
        self.assertSuccess(response)
        meta = json.loads(response.content)['meta']
        self.assertEqual(meta['foo'], 'bar')

    @assert_backend_closed
    def test_get_invalid_metadata(self, backend):
        backend.return_value.get_image.return_value = self.image
        response = self.myget('images/42/metadata/not_found', 'user')
        self.assertItemNotFound(response)

    def test_delete_metadata_item(self, backend):
        backend.return_value.get_image.return_value = self.image
        response = self.mydelete('images/42/metadata/foo', 'user')
        self.assertEqual(response.status_code, 204)
        backend.return_value.update_metadata.assert_called_once_with('42', {'properties': {'foo2':
                                                    'bar2'}})

    @assert_backend_closed
    def test_create_metadata_item(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'meta': {'foo3': 'bar3'}}
        response = self.myput('images/42/metadata/foo3', 'user',
                              json.dumps(request), 'json')
        self.assertEqual(response.status_code, 201)
        backend.return_value.update_metadata.assert_called_once_with('42',
                {'properties':
                    {'foo': 'bar', 'foo2': 'bar2', 'foo3': 'bar3'}})

    @assert_backend_closed
    def test_create_metadata_malformed_1(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'met': {'foo3': 'bar3'}}
        response = self.myput('images/42/metadata/foo3', 'user',
                              json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_create_metadata_malformed_2(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'metadata': [('foo3', 'bar3')]}
        response = self.myput('images/42/metadata/foo3', 'user',
                              json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_create_metadata_malformed_3(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'met': {'foo3': 'bar3', 'foo4': 'bar4'}}
        response = self.myput('images/42/metadata/foo3', 'user',
                                json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_create_metadata_malformed_4(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'met': {'foo3': 'bar3'}}
        response = self.myput('images/42/metadata/foo4', 'user',
                              json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_update_metadata_item(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'metadata': {'foo': 'bar_new', 'foo4': 'bar4'}}
        response = self.mypost('images/42/metadata', 'user',
                               json.dumps(request), 'json')
        self.assertEqual(response.status_code, 201)
        backend.return_value.update_metadata.assert_called_once_with('42',
                {'properties':
                    {'foo': 'bar_new', 'foo2': 'bar2', 'foo4': 'bar4'}
                })

    @assert_backend_closed
    def test_update_metadata_malformed(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'meta': {'foo': 'bar_new', 'foo4': 'bar4'}}
        response = self.mypost('images/42/metadata', 'user',
                               json.dumps(request), 'json')
        self.assertBadRequest(response)
