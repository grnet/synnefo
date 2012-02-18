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

from django.conf.urls.defaults import patterns
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from synnefo.api import util
from synnefo.api.common import method_not_allowed
from synnefo.api.faults import BadRequest
from synnefo.db.models import Image, ImageMetadata
from synnefo.util.log import getLogger


log = getLogger('synnefo.api')

urlpatterns = patterns('synnefo.api.images',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_images', {'detail': True}),
    (r'^/(\d+)(?:.json|.xml)?$', 'image_demux'),
    (r'^/(\d+)/meta(?:.json|.xml)?$', 'metadata_demux'),
    (r'^/(\d+)/meta/(.+?)(?:.json|.xml)?$', 'metadata_item_demux'),
)

def demux(request):
    if request.method == 'GET':
        return list_images(request)
    elif request.method == 'POST':
        return create_image(request)
    else:
        return method_not_allowed(request)

def image_demux(request, image_id):
    if request.method == 'GET':
        return get_image_details(request, image_id)
    elif request.method == 'DELETE':
        return delete_image(request, image_id)
    else:
        return method_not_allowed(request)

def metadata_demux(request, image_id):
    if request.method == 'GET':
        return list_metadata(request, image_id)
    elif request.method == 'POST':
        return update_metadata(request, image_id)
    else:
        return method_not_allowed(request)

def metadata_item_demux(request, image_id, key):
    if request.method == 'GET':
        return get_metadata_item(request, image_id, key)
    elif request.method == 'PUT':
        return create_metadata_item(request, image_id, key)
    elif request.method == 'DELETE':
        return delete_metadata_item(request, image_id, key)
    else:
        return method_not_allowed(request)


def image_to_dict(image, detail=True):
    d = {'id': image.id, 'name': image.name}
    if detail:
        d['updated'] = util.isoformat(image.updated)
        d['created'] = util.isoformat(image.created)
        d['status'] = image.state
        d['progress'] = 100 if image.state == 'ACTIVE' else 0
        if image.sourcevm:
            d['serverRef'] = image.sourcevm.id

        metadata = {}
        for meta in ImageMetadata.objects.filter(image=image):
            metadata[meta.meta_key] = meta.meta_value

        if metadata:
            d['metadata'] = {'values': metadata}

    return d


@util.api_method('GET')
def list_images(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)
    
    log.debug('list_images detail=%s', detail)
    user_images = Image.objects.filter(Q(owner=request.user) | Q(public=True))
    since = util.isoparse(request.GET.get('changes-since'))
    
    if since:
        user_images = user_images.filter(updated__gte=since)
        if not user_images:
            return HttpResponse(status=304)
    else:
        user_images = user_images.exclude(state='DELETED')
    
    images = [image_to_dict(image, detail) for image in user_images]
    
    if request.serialization == 'xml':
        data = render_to_string('list_images.xml', {
            'images': images,
            'detail': detail})
    else:
        data = json.dumps({'images': {'values': images}})

    return HttpResponse(data, status=200)

@util.api_method('POST')
def create_image(request):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       serverCapacityUnavailable (503),
    #                       buildInProgress (409),
    #                       resizeNotAllowed (403),
    #                       backupOrResizeInProgress (409),
    #                       overLimit (413)
    
    raise ServiceUnavailable('Create image not supported')


@util.api_method('GET')
def get_image_details(request, image_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)
    
    log.debug('get_image_details %s', image_id)
    image = util.get_image(image_id, request.user)
    imagedict = image_to_dict(image)

    if request.serialization == 'xml':
        data = render_to_string('image.xml', {'image': imagedict})
    else:
        data = json.dumps({'image': imagedict})

    return HttpResponse(data, status=200)

@util.api_method('DELETE')
def delete_image(request, image_id):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       overLimit (413)
    
    log.debug('delete_image %s', image_id)
    image = util.get_image(image_id, request.user)
    image.state = 'DELETED'
    image.save()
    log.info('User %d deleted image %d', request.user.id, image.id)
    return HttpResponse(status=204)

@util.api_method('GET')
def list_metadata(request, image_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)
    
    log.debug('list_image_metadata %s', image_id)
    image = util.get_image(image_id, request.user)
    metadata = dict((m.meta_key, m.meta_value) for m in image.metadata.all())
    return util.render_metadata(request, metadata, use_values=True, status=200)

@util.api_method('POST')
def update_metadata(request, image_id):
    # Normal Response Code: 201
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       overLimit (413)
    
    req = util.get_request_dict(request)
    log.debug('update_image_metadata %s %s', image_id, req)
    image = util.get_image(image_id, request.user)
    try:
        metadata = req['metadata']
        assert isinstance(metadata, dict)
    except (KeyError, AssertionError):
        raise BadRequest('Malformed request.')
    
    for key, val in metadata.items():
        meta, created = image.metadata.get_or_create(meta_key=key)
        meta.meta_value = val
        meta.save()
    
    image.save()
    image_meta = dict((m.meta_key, m.meta_value) for m in image.metadata.all())
    return util.render_metadata(request, image_meta, status=201)

@util.api_method('GET')
def get_metadata_item(request, image_id, key):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       overLimit (413)
    
    log.debug('get_image_metadata_item %s %s', image_id, key)
    image = util.get_image(image_id, request.user)
    meta = util.get_image_meta(image, key)
    return util.render_meta(request, meta, status=200)

@util.api_method('PUT')
def create_metadata_item(request, image_id, key):
    # Normal Response Code: 201
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       overLimit (413)
    
    req = util.get_request_dict(request)
    log.debug('create_image_metadata_item %s %s %s', image_id, key, req)
    image = util.get_image(image_id, request.user)
    try:
        metadict = req['meta']
        assert isinstance(metadict, dict)
        assert len(metadict) == 1
        assert key in metadict
    except (KeyError, AssertionError):
        raise BadRequest('Malformed request.')
    
    meta, created = ImageMetadata.objects.get_or_create(
        meta_key=key,
        image=image)
    
    meta.meta_value = metadict[key]
    meta.save()
    image.save()
    return util.render_meta(request, meta, status=201)

@util.api_method('DELETE')
def delete_metadata_item(request, image_id, key):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       overLimit (413),
    
    log.debug('delete_image_metadata_item %s %s', image_id, key)
    image = util.get_image(image_id, request.user)
    meta = util.get_image_meta(image, key)
    meta.delete()
    image.save()
    return HttpResponse(status=204)
