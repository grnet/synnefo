# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from logging import getLogger

import dateutil.parser

from django.conf.urls.defaults import patterns
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from contextlib import contextmanager

from synnefo.api import util
from synnefo.api.common import method_not_allowed
from synnefo.api.faults import BadRequest, ItemNotFound, ServiceUnavailable
from synnefo.api.util import api_method, isoformat, isoparse
from synnefo.plankton.backend import ImageBackend


log = getLogger('synnefo.api')

urlpatterns = patterns(
    'synnefo.api.images',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_images', {'detail': True}),
    (r'^/([\w-]+)(?:.json|.xml)?$', 'image_demux'),
    (r'^/([\w-]+)/meta(?:.json|.xml)?$', 'metadata_demux'),
    (r'^/([\w-]+)/meta/(.+?)(?:.json|.xml)?$', 'metadata_item_demux')
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
    d = dict(id=image['id'], name=image['name'])
    if detail:
        d['updated'] = isoformat(dateutil.parser.parse(image['updated_at']))
        d['created'] = isoformat(dateutil.parser.parse(image['created_at']))
        d['status'] = 'DELETED' if image['deleted_at'] else 'ACTIVE'
        d['progress'] = 100 if image['status'] == 'available' else 0
        if image['properties']:
            d['metadata'] = {'values': image['properties']}
    return d


@contextmanager
def image_backend(userid):
    backend = ImageBackend(userid)
    try:
        yield backend
    finally:
        backend.close()


@api_method('GET')
def list_images(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('list_images detail=%s', detail)
    with image_backend(request.user_uniq) as backend:
        since = isoparse(request.GET.get('changes-since'))
        if since:
            images = []
            for image in backend.iter():
                updated = dateutil.parser.parse(image['updated_at'])
                if updated >= since:
                    images.append(image)
            if not images:
                return HttpResponse(status=304)
        else:
            images = backend.list()

    images = sorted(images, key=lambda x: x['id'])
    reply = [image_to_dict(image, detail) for image in images]

    if request.serialization == 'xml':
        data = render_to_string('list_images.xml',
                                dict(images=reply, detail=detail))
    else:
        data = json.dumps(dict(images={'values': reply}))

    return HttpResponse(data, status=200)


@api_method('POST')
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

    raise ServiceUnavailable('Not supported.')


@api_method('GET')
def get_image_details(request, image_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)

    log.debug('get_image_details %s', image_id)
    image = util.get_image(image_id, request.user_uniq)
    reply = image_to_dict(image)

    if request.serialization == 'xml':
        data = render_to_string('image.xml', dict(image=reply))
    else:
        data = json.dumps(dict(image=reply))

    return HttpResponse(data, status=200)


@api_method('DELETE')
def delete_image(request, image_id):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       overLimit (413)

    log.info('delete_image %s', image_id)
    with image_backend(request.user_uniq) as backend:
        backend.delete(image_id)
    log.info('User %s deleted image %s', request.user_uniq, image_id)
    return HttpResponse(status=204)


@api_method('GET')
def list_metadata(request, image_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('list_image_metadata %s', image_id)
    image = util.get_image(image_id, request.user_uniq)
    metadata = image['properties']
    return util.render_metadata(request, metadata, use_values=True, status=200)


@api_method('POST')
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
    log.info('update_image_metadata %s %s', image_id, req)
    image = util.get_image(image_id, request.user_uniq)
    try:
        metadata = req['metadata']
        assert isinstance(metadata, dict)
    except (KeyError, AssertionError):
        raise BadRequest('Malformed request.')

    properties = image['properties']
    properties.update(metadata)

    with image_backend(request.user_uniq) as backend:
        backend.update(image_id, dict(properties=properties))

    return util.render_metadata(request, properties, status=201)


@api_method('GET')
def get_metadata_item(request, image_id, key):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('get_image_metadata_item %s %s', image_id, key)
    image = util.get_image(image_id, request.user_uniq)
    val = image['properties'].get(key)
    if val is None:
        raise ItemNotFound('Metadata key not found.')
    return util.render_meta(request, {key: val}, status=200)


@api_method('PUT')
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
    log.info('create_image_metadata_item %s %s %s', image_id, key, req)
    try:
        metadict = req['meta']
        assert isinstance(metadict, dict)
        assert len(metadict) == 1
        assert key in metadict
    except (KeyError, AssertionError):
        raise BadRequest('Malformed request.')

    val = metadict[key]
    image = util.get_image(image_id, request.user_uniq)
    properties = image['properties']
    properties[key] = val

    with image_backend(request.user_uniq) as backend:
        backend.update(image_id, dict(properties=properties))

    return util.render_meta(request, {key: val}, status=201)


@api_method('DELETE')
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

    log.info('delete_image_metadata_item %s %s', image_id, key)
    image = util.get_image(image_id, request.user_uniq)
    properties = image['properties']
    properties.pop(key, None)

    with image_backend(request.user_uniq) as backend:
        backend.update(image_id, dict(properties=properties))

    return HttpResponse(status=204)
