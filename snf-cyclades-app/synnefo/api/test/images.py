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
from synnefo.api.tests import BaseAPITest

from mock import patch
from functools import wraps


def assert_backend_closed(func):
    """Decorator for ensuring that ImageBackend is returned to pool."""
    @wraps(func)
    def wrapper(self, backend):
        result = func(self, backend)
        if backend.called is True:
            num = len(backend.mock_calls) / 2
            assert(len(backend.return_value.close.mock_calls), num)
        return result
    return wrapper


@patch('synnefo.plankton.utils.ImageBackend')
class ImageAPITest(BaseAPITest):
    @assert_backend_closed
    def test_create_image(self, mimage):
        """Test that create image is not implemented"""
        response = self.post('/api/v1.1/images/', 'user', json.dumps(''),
                             'json')
        self.assertEqual(response.status_code, 501)

    @assert_backend_closed
    def test_list_images(self, mimage):
        """Test that expected list of images is returned"""
        images = [{'id': 1, 'name': 'image-1'},
                  {'id': 2, 'name': 'image-2'},
                  {'id': 3, 'name': 'image-3'}]
        mimage().list.return_value = images
        response = self.get('/api/v1.1/images/', 'user')
        self.assertSuccess(response)
        api_images = json.loads(response.content)['images']['values']
        self.assertEqual(images, api_images)

    @assert_backend_closed
    def test_list_images_detail(self, mimage):
        images = [{'id': 1,
                   'name': 'image-1',
                   'status':'available',
                   'created_at': '2012-11-26 11:52:54',
                   'updated_at': '2012-12-26 11:52:54',
                   'deleted_at': '',
                   'properties': {'foo':'bar'}},
                  {'id': 2,
                   'name': 'image-2',
                   'status': 'deleted',
                   'created_at': '2012-11-26 11:52:54',
                   'updated_at': '2012-12-26 11:52:54',
                   'deleted_at': '2012-12-27 11:52:54',
                   'properties': ''},
                  {'id': 3,
                   'name': 'image-3',
                   'status': 'available',
                   'created_at': '2012-11-26 11:52:54',
                   'deleted_at': '',
                   'updated_at': '2012-12-26 11:52:54',
                   'properties': ''}]
        result_images = [
                  {'id': 1,
                   'name': 'image-1',
                   'status':'ACTIVE',
                   'progress': 100,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00',
                   'metadata': {'values': {'foo':'bar'}}},
                  {'id': 2,
                   'name': 'image-2',
                   'status': 'DELETED',
                   'progress': 0,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00'},
                  {'id': 3,
                   'name': 'image-3',
                   'status': 'ACTIVE',
                   'progress': 100,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00'}]
        mimage().list.return_value = images
        response = self.get('/api/v1.1/images/detail', 'user')
        self.assertSuccess(response)
        api_images = json.loads(response.content)['images']['values']
        self.assertEqual(len(result_images), len(api_images))
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
                   'properties': ''},
                  {'id': 2,
                   'name': 'image-2',
                   'status': 'deleted',
                   'progress': 0,
                   'created_at': new_time.isoformat(),
                   'updated_at': new_time.isoformat(),
                   'deleted_at': new_time.isoformat(),
                   'properties': ''}]
        mimage().iter.return_value = images
        response =\
            self.get('/api/v1.1/images/detail?changes-since=%sUTC' % new_time)
        self.assertSuccess(response)
        api_images = json.loads(response.content)['images']['values']
        self.assertEqual(1, len(api_images))

    @assert_backend_closed
    def test_get_image_details(self, mimage):
        image = {'id': 42,
                 'name': 'image-1',
                 'status': 'available',
                 'created_at': '2012-11-26 11:52:54',
                 'updated_at': '2012-12-26 11:52:54',
                 'deleted_at': '',
                 'properties': {'foo': 'bar'}}
        result_image = \
                  {'id': 42,
                   'name': 'image-1',
                   'status': 'ACTIVE',
                   'progress': 100,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00',
                   'metadata': {'values': {'foo': 'bar'}}}
        with patch('synnefo.api.util.get_image') as m:
            m.return_value = image
            response = self.get('/api/v1.1/images/42', 'user')
        self.assertSuccess(response)
        api_image = json.loads(response.content)['image']
        self.assertEqual(api_image, result_image)

    @assert_backend_closed
    def test_invalid_image(self, mimage):
        with patch('synnefo.api.util.get_image') as m:
            m.side_effect = faults.ItemNotFound('Image not found')
            response = self.get('/api/v1.1/images/42', 'user')
        self.assertItemNotFound(response)

    def test_delete_image(self, mimage):
        response = self.delete("/api/v1.1/images/42", "user")
        self.assertEqual(response.status_code, 204)
        mimage.return_value.unregister.assert_called_once_with('42')
        mimage.return_value._delete.assert_not_called('42')


@patch('synnefo.plankton.utils.ImageBackend')
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
                   'metadata': {'values': {'foo': 'bar'}}}

    @assert_backend_closed
    def test_list_metadata(self, backend):
        backend.return_value.get_image.return_value = self.image
        response = self.get('/api/v1.1/images/42/meta', 'user')
        self.assertSuccess(response)
        meta = json.loads(response.content)['metadata']['values']
        self.assertEqual(meta, self.image['properties'])

    @assert_backend_closed
    def test_get_metadata(self, backend):
        backend.return_value.get_image.return_value = self.image
        response = self.get('/api/v1.1/images/42/meta/foo', 'user')
        self.assertSuccess(response)
        meta = json.loads(response.content)['meta']
        self.assertEqual(meta['foo'], 'bar')

    @assert_backend_closed
    def test_get_invalid_metadata(self, backend):
        backend.return_value.get_image.return_value = self.image
        response = self.get('/api/v1.1/images/42/meta/not_found', 'user')
        self.assertItemNotFound(response)

    def test_delete_metadata_item(self, backend):
        backend.return_value.get_image.return_value = self.image
        response = self.delete('/api/v1.1/images/42/meta/foo', 'user')
        self.assertEqual(response.status_code, 204)
        backend.return_value.update.assert_called_once_with('42', {'properties': {'foo2':
                                                    'bar2'}})

    @assert_backend_closed
    def test_create_metadata_item(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'meta': {'foo3': 'bar3'}}
        response = self.put('/api/v1.1/images/42/meta/foo3', 'user',
                            json.dumps(request), 'json')
        self.assertEqual(response.status_code, 201)
        backend.return_value.update.assert_called_once_with('42',
                {'properties':
                    {'foo': 'bar', 'foo2': 'bar2', 'foo3': 'bar3'}})

    @assert_backend_closed
    def test_create_metadata_malformed_1(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'met': {'foo3': 'bar3'}}
        response = self.put('/api/v1.1/images/42/meta/foo3', 'user',
                            json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_create_metadata_malformed_2(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'meta': [('foo3', 'bar3')]}
        response = self.put('/api/v1.1/images/42/meta/foo3', 'user',
                            json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_create_metadata_malformed_3(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'met': {'foo3': 'bar3', 'foo4': 'bar4'}}
        response = self.put('/api/v1.1/images/42/meta/foo3', 'user',
                                json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_create_metadata_malformed_4(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'met': {'foo3': 'bar3'}}
        response = self.put('/api/v1.1/images/42/meta/foo4', 'user',
                                json.dumps(request), 'json')
        self.assertBadRequest(response)

    @assert_backend_closed
    def test_update_metadata_item(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'metadata': {'foo': 'bar_new', 'foo4': 'bar4'}}
        response = self.post('/api/v1.1/images/42/meta', 'user',
                             json.dumps(request), 'json')
        self.assertEqual(response.status_code, 201)
        backend.return_value.update.assert_called_once_with('42',
                {'properties':
                    {'foo': 'bar_new', 'foo2': 'bar2', 'foo4': 'bar4'}
                })

    @assert_backend_closed
    def test_update_metadata_malformed(self, backend):
        backend.return_value.get_image.return_value = self.image
        request = {'meta': {'foo': 'bar_new', 'foo4': 'bar4'}}
        response = self.post('/api/v1.1/images/42/meta', 'user',
                            json.dumps(request), 'json')
        self.assertBadRequest(response)
