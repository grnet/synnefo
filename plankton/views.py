# Copyright 2011 GRNET S.A. All rights reserved.
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

from string import punctuation

from django.conf import settings
from django.http import (HttpResponse, HttpResponseNotAllowed,
        HttpResponseNotFound)

from synnefo.plankton.util import plankton_method
from synnefo.util.log import getLogger


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

log = getLogger('synnefo.plankton')


def demux(request):
    if request.method == 'GET':
        return list_public(request)
    elif request.method == 'POST':
        return add(request)
    else:
        return HttpResponseNotAllowed(['GET', 'POST'])

def image_demux(request, image_id):
    if request.method == 'GET':
        return get(request, image_id)
    elif request.method == 'HEAD':
        return get_meta(request, image_id)
    elif request.method == 'PUT':
        return update(request, image_id)
    else:
        return HttpResponseNotAllowed(['GET', 'HEAD', 'PUT'])


def create_image_response(image):
    response = HttpResponse()
    
    for key in DETAIL_FIELDS:
        if key == 'properties':
            for k, v in image.get('properties', {}).items():
                name = 'x-image-meta-property-' + k.replace('_', '-')
                response[name] = v
        else:
            name = 'x-image-meta-' + key.replace('_', '-')
            response[name] = image.get(key, '')
    
    return response


def get_image_headers(request):
    def normalize(s):
        return ''.join('_' if c in punctuation else c.lower() for c in s)
    
    META_PREFIX = 'HTTP_X_IMAGE_META_'
    META_PREFIX_LEN = len(META_PREFIX)
    META_PROPERTY_PREFIX = 'HTTP_X_IMAGE_META_PROPERTY_'
    META_PROPERTY_PREFIX_LEN = len(META_PROPERTY_PREFIX)
    
    headers = {'properties': {}}
    
    for key, val in request.META.items():
        if key.startswith(META_PROPERTY_PREFIX):
            name = normalize(key[META_PROPERTY_PREFIX_LEN:])
            headers['properties'][name] = val
        elif key.startswith(META_PREFIX):
            name = normalize(key[META_PREFIX_LEN:])
            headers[name] = val
    
    is_public = headers.get('is_public', None)
    if is_public is not None:
        headers['is_public'] = True if is_public.lower() == 'true' else False
    
    if not headers['properties']:
        del headers['properties']
    
    return headers


@plankton_method('POST')
def add(request):
    """Add a new virtual machine image"""
    
    params = get_image_headers(request)
    log.debug('add %s', params)
    
    assert set(params.keys()).issubset(set(ADD_FIELDS))
    
    if 'id' in params:
        return HttpResponse(status=409)     # Custom IDs are not supported
    
    if 'location' in params:
        image = request.backend.register_image(**params)
    else:
        params['data'] = request.raw_post_data
        image = request.backend.put_image(**params)
    
    if not image:
        return HttpResponse(status=500)
    return create_image_response(image)


@plankton_method('GET')
def get(request, image_id):
    """Retrieve a virtual machine image"""
    
    image = request.backend.get_image(image_id)
    if not image:
        return HttpResponseNotFound()
    
    response = create_image_response(image)
    data = request.backend.get_image_data(image)
    response.content = data
    response['Content-Length'] = len(data)
    response['Content-Type'] = 'application/octet-stream'
    response['ETag'] = image['checksum']
    return response


@plankton_method('HEAD')
def get_meta(request, image_id):
    """Return detailed metadata on a specific image"""

    image = request.backend.get_image(image_id)
    if not image:
        return HttpResponseNotFound()
    return create_image_response(image)


@plankton_method('GET')
def list_public(request, detail=False):
    """Return a list of public VM images."""

    def get_request_params(keys):
        params = {}
        for key in keys:
            val = request.GET.get(key, None)
            if val is not None:
                params[key] = val
        return params

    log.debug('list_public detail=%s', detail)

    filters = get_request_params(FILTERS)
    params = get_request_params(PARAMS)

    params.setdefault('sort_key', 'created_at')
    params.setdefault('sort_dir', 'desc')

    assert params['sort_key'] in SORT_KEY_OPTIONS
    assert params['sort_dir'] in SORT_DIR_OPTIONS

    images = request.backend.list_public_images(filters, params)
    
    # Remove keys that should not be returned
    fields = DETAIL_FIELDS if detail else LIST_FIELDS
    for image in images:
        for key in image.keys():
            if key not in fields:
                del image[key]

    data = json.dumps(images, indent=settings.DEBUG)
    return HttpResponse(data)


@plankton_method('PUT')
def update(request, image_id):
    """Updating an Image"""
    
    meta = get_image_headers(request)
    log.debug('update %s', meta)
    
    assert set(meta.keys()).issubset(set(UPDATE_FIELDS))
    
    image = request.backend.update_image(image_id, meta)
    
    if not image:
        return HttpResponse(status=500)
    return create_image_response(image)
    