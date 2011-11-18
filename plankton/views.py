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


SHORT_IMAGE_META = ('id', 'status', 'name', 'disk_format', 'container_format',
                    'size')

IMAGE_META = SHORT_IMAGE_META + ('checksum', 'location', 'created_at',
                            'updated_at', 'deleted_at', 'is_public', 'owner')


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
    else:
        return HttpResponseNotAllowed(['GET', 'HEAD'])


@plankton_method('GET')
def list_public(request, detail=False):
    """Return a list of public VM images."""
    
    log.debug('list_public detail=%s', detail)
    
    kwargs = {}   # Args to be passed to list_public_images
    for key in ('name', 'container_format', 'disk_format', 'status',
                'size_min', 'size_max', 'sort_key', 'sort_dir'):
        val = request.GET.get(key)
        if val is None:
            continue
        if key in ('size_min', 'size_max') and val is not None:
            val = int(val)
        kwargs[key] = val
    
    images = request.backend.list_public_images(**kwargs)
    
    # Remove keys that should not be returned
    if detail:
        image_keys = IMAGE_META + ('properties',)
    else:
        image_keys = SHORT_IMAGE_META
    for image in images:
        for key in image.keys():
            if key not in image_keys:
                del image[key]
    
    data = json.dumps(images, indent=settings.DEBUG)
    return HttpResponse(data)


def _set_response_headers(response, image):
    for key in IMAGE_META:
        name = 'x-image-meta-' + key.replace('_', '-')
        response[name] = image.get(key, '')
    for key, val in image.get('properties', {}).items():
        name = 'x-image-meta-property-' + key
        response[name] = val


@plankton_method('HEAD')
def get_meta(request, image_id):
    """Return detailed metadata on a specific image"""
    
    image = request.backend.get_public_image(image_id)
    if not image:
        return HttpResponseNotFound()
    
    response = HttpResponse()
    _set_response_headers(response, image)
    return response


@plankton_method('GET')
def get(request, image_id):
    """Retrieve a virtual machine image"""
    
    image = request.backend.get_public_image(image_id)
    if not image:
        return HttpResponseNotFound()
    
    response = HttpResponse()
    _set_response_headers(response, image)
    data = request.backend.get_image_data(image)
    response.content = data
    response['Content-Length'] = len(data)
    response['Content-Type'] = 'application/octet-stream'
    response['ETag'] = image['checksum']
    return response


@plankton_method('POST')
def add(request):
    if request.META.get('HTTP_X_IMAGE_META_ID'):
        return HttpResponse(status=409)     # Custom IDs are not supported
    
    kwargs = {}    # Args for 'put_image' or 'register_image'
    for key in ('name', 'store', 'disk_format', 'container_format', 'size',
                'checksum', 'owner', 'location'):
        name = 'HTTP_X_IMAGE_META_' + key.upper()
        val = request.META.get(name)
        if val is not None:
            kwargs[key] = val
    
    log.debug('add %s', kwargs)
    
    if request.META.get('HTTP_X_IMAGE_META_IS_PUBLIC', '').lower() == 'true':
        kwargs['is_public'] = True
    else:
        kwargs['is_public'] = False
    
    properties = {}
    META_PROPERTY_PREFIX = 'HTTP_X_IMAGE_META_PROPERTY_'
    META_PROPERTY_PREFIX_LEN = len(META_PROPERTY_PREFIX)
    for key, val in request.META.items():
        if key.startswith(META_PROPERTY_PREFIX):
            name = ''.join(c.lower() if c not in punctuation else '_'
                           for c in key[META_PROPERTY_PREFIX_LEN:])
            properties[name] = val
    
    log.debug('add properties=%s', properties)
    
    kwargs['properties'] = properties
    
    if 'location' in kwargs:
        image = request.backend.register_image(**kwargs)
    else:
        kwargs['data'] = request.raw_post_data
        image = request.backend.put_image(**kwargs)
    
    if not image:
        return HttpResponse(status=500)
    
    response = HttpResponse()
    _set_response_headers(response, image)
    return response
