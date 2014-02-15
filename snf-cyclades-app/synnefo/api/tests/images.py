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

compute_path = get_service_path(cyclades_services, 'compute',
                                version='v2.0')
IMAGES_URL = join_urls(compute_path, "images/")


def assert_backend_closed(func):
    """Decorator for ensuring that PlanktonBackend is returned to pool."""
    @wraps(func)
    def wrapper(self, backend):
        result = func(self, backend)
        if backend.called is True:
            backend.return_value.close.asssert_called
        return result
    return wrapper


@patch('synnefo.plankton.backend.PlanktonBackend')
class ImageAPITest(BaseAPITest):
    @assert_backend_closed
    def test_create_image(self, mimage):
        """Test that create image is not implemented"""
        response = self.post(IMAGES_URL, 'user', json.dumps(''), 'json')
        self.assertEqual(response.status_code, 501)

    @assert_backend_closed
    def test_list_images(self, mimage):
        """Test that expected list of images is returned"""
        images = [{'id': 1, 'name': 'image-1'},
                  {'id': 2, 'name': 'image-2'},
                  {'id': 3, 'name': 'image-3'}]
        mimage().__enter__().list_images.return_value = images
        response = self.get(IMAGES_URL, 'user')
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
        mimage().__enter__().list_images.return_value = images
        response = self.get(join_urls(IMAGES_URL, "detail"), 'user')
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
        mimage().__enter__().list_images.return_value = images
        response =\
            self.get(join_urls(IMAGES_URL, 'detail?changes-since=%sUTC' %
                               new_time))
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
        mimage().__enter__().get_image.return_value = image
        response = self.get(join_urls(IMAGES_URL, "42"), 'user')
        self.assertSuccess(response)
        api_image = json.loads(response.content)['image']
        api_image.pop("links")
        self.assertEqual(api_image, result_image)

    def test_invalid_image(self, mimage):
        mimage().__enter__().get_image.side_effect = \
            faults.ItemNotFound('Image not found')
        response = self.get(join_urls(IMAGES_URL, "42"), 'user')
        self.assertItemNotFound(response)

    @assert_backend_closed
    def test_delete_image(self, mimage):
        response = self.delete(join_urls(IMAGES_URL, "42"), 'user')
        self.assertEqual(response.status_code, 204)
        mimage().__enter__().unregister.assert_called_once_with('42')

    @assert_backend_closed
    def test_catch_wrong_api_paths(self, *args):
        response = self.get(join_urls(IMAGES_URL, 'nonexistent/lala/foo'))
        self.assertEqual(response.status_code, 400)
        try:
            error = json.loads(response.content)
        except ValueError:
            self.assertTrue(False)

    @assert_backend_closed
    def test_method_not_allowed(self, *args):
        # /images/ allows only POST, GET
        response = self.put(IMAGES_URL, '', '')
        self.assertMethodNotAllowed(response)
        response = self.delete(IMAGES_URL, '')
        self.assertMethodNotAllowed(response)

        # /images/<imgid>/ allows only GET, DELETE
        response = self.post(join_urls(IMAGES_URL, "42"), 'user')
        self.assertMethodNotAllowed(response)
        response = self.put(join_urls(IMAGES_URL, "42"), 'user')
        self.assertMethodNotAllowed(response)

        # /images/<imgid>/metadata/ allows only POST, GET
        response = self.put(join_urls(IMAGES_URL, "42", "metadata"), 'user')
        self.assertMethodNotAllowed(response)
        response = self.delete(join_urls(IMAGES_URL, "42", "metadata"), 'user')
        self.assertMethodNotAllowed(response)

        # /images/<imgid>/metadata/<key> allows only PUT, GET, DELETE
        response = self.post(join_urls(IMAGES_URL, "42", "metadata", "foo"),
                             'user')
        self.assertMethodNotAllowed(response)


@patch('synnefo.plankton.backend.PlanktonBackend')
class ImageMetadataAPITest(BaseAPITest):
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
        backend().__enter__().get_image.return_value = self.image
        response = self.get(join_urls(IMAGES_URL, '42/metadata'), 'user')
        self.assertSuccess(response)
        meta = json.loads(response.content)['metadata']
        self.assertEqual(meta, self.image['properties'])

    @assert_backend_closed
    def test_get_metadata(self, backend):
        backend().__enter__().get_image.return_value = self.image
        response = self.get(join_urls(IMAGES_URL, '42/metadata/foo'), 'user')
        self.assertSuccess(response)
        meta = json.loads(response.content)['meta']
        self.assertEqual(meta['foo'], 'bar')

    @assert_backend_closed
    def test_get_invalid_metadata(self, backend):
        backend().__enter__().get_image.return_value = self.image
        response = self.get(join_urls(IMAGES_URL, '42/metadata/not_found'),
                            'user')
        self.assertItemNotFound(response)

    def test_delete_metadata_item(self, backend):
        backend().__enter__().get_image.return_value = self.image
        response = self.delete(join_urls(IMAGES_URL, '42/metadata/foo'),
                               'user')
        self.assertEqual(response.status_code, 204)
        backend().__enter__().update_metadata\
               .assert_called_once_with('42', {'properties': {'foo2': 'bar2'}})

    @assert_backend_closed
    def test_create_metadata_item(self, backend):
        backend().__enter__().get_image.return_value = self.image
        request = {'meta': {'foo3': 'bar3'}}
        response = self.put(join_urls(IMAGES_URL, '42/metadata/foo3'), 'user',
                            json.dumps(request), 'json')
        self.assertEqual(response.status_code, 201)
        backend().__enter__().update_metadata.assert_called_once_with('42',
                {'properties':
                    {'foo': 'bar', 'foo2': 'bar2', 'foo3': 'bar3'}})

    @assert_backend_closed
    def test_create_metadata_malformed_1(self, backend):
        backend().__enter__().get_image.return_value = self.image
        request = {'met': {'foo3': 'bar3'}}
        response = self.put(join_urls(IMAGES_URL, '42/metadata/foo3'), 'user',
                            json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_create_metadata_malformed_2(self, backend):
        backend().__enter__().get_image.return_value = self.image
        request = {'metadata': [('foo3', 'bar3')]}
        response = self.put(join_urls(IMAGES_URL, '42/metadata/foo3'), 'user',
                            json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_create_metadata_malformed_3(self, backend):
        backend().__enter__().get_image.return_value = self.image
        request = {'met': {'foo3': 'bar3', 'foo4': 'bar4'}}
        response = self.put(join_urls(IMAGES_URL, '42/metadata/foo3'), 'user',
                            json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_create_metadata_malformed_4(self, backend):
        backend().__enter__().get_image.return_value = self.image
        request = {'met': {'foo3': 'bar3'}}
        response = self.put(join_urls(IMAGES_URL, '42/metadata/foo4'), 'user',
                            json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_update_metadata_item(self, backend):
        backend().__enter__().get_image.return_value = self.image
        request = {'metadata': {'foo': 'bar_new', 'foo4': 'bar4'}}
        response = self.post(join_urls(IMAGES_URL, '42/metadata'), 'user',
                             json.dumps(request), 'json')
        self.assertEqual(response.status_code, 201)
        backend().__enter__().update_metadata.assert_called_once_with('42',
                {'properties':
                    {'foo': 'bar_new', 'foo2': 'bar2', 'foo4': 'bar4'}
                })

    @assert_backend_closed
    def test_update_metadata_malformed(self, backend):
        backend().__enter__().get_image.return_value = self.image
        request = {'meta': {'foo': 'bar_new', 'foo4': 'bar4'}}
        response = self.post(join_urls(IMAGES_URL, '42/metadata'), 'user',
                             json.dumps(request), 'json')
        self.assertBadRequest(response)
