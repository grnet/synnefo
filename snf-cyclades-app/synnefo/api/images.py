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

from logging import getLogger
from itertools import ifilter

from dateutil.parser import parse as date_parse

from django.conf.urls import patterns
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from snf_django.lib import api
from snf_django.lib.api import faults, utils
from synnefo.api import util
from synnefo.plankton import backend


log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.images',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_images', {'detail': True}),
    (r'^/([\w-]+)(?:.json|.xml)?$', 'image_demux'),
    (r'^/([\w-]+)/metadata(?:.json|.xml)?$', 'metadata_demux'),
    (r'^/([\w-]+)/metadata/(.+?)(?:.json|.xml)?$', 'metadata_item_demux')
)


def demux(request):
    if request.method == 'GET':
        return list_images(request)
    elif request.method == 'POST':
        return create_image(request)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'POST'])


def image_demux(request, image_id):
    if request.method == 'GET':
        return get_image_details(request, image_id)
    elif request.method == 'DELETE':
        return delete_image(request, image_id)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'DELETE'])


def metadata_demux(request, image_id):
    if request.method == 'GET':
        return list_metadata(request, image_id)
    elif request.method == 'POST':
        return update_metadata(request, image_id)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'POST'])


def metadata_item_demux(request, image_id, key):
    if request.method == 'GET':
        return get_metadata_item(request, image_id, key)
    elif request.method == 'PUT':
        return create_metadata_item(request, image_id, key)
    elif request.method == 'DELETE':
        return delete_metadata_item(request, image_id, key)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET',
                                                           'PUT',
                                                           'DELETE'])


API_STATUS_FROM_IMAGE_STATUS = {
    "CREATING": "SAVING",
    "AVAILABLE": "ACTIVE",
    "ERROR": "ERROR",
    "DELETED": "DELETED"}


def image_to_dict(image, detail=True):
    d = dict(id=image['id'], name=image['name'])
    if detail:
        d['updated'] = utils.isoformat(date_parse(image['updated_at']))
        d['created'] = utils.isoformat(date_parse(image['created_at']))
        img_status = image.get("status", "").upper()
        status = API_STATUS_FROM_IMAGE_STATUS.get(img_status, "UNKNOWN")
        d['status'] = status
        d['progress'] = 100 if status == 'ACTIVE' else 0
        d['user_id'] = image['owner']
        d['tenant_id'] = image['owner']
        d['public'] = image["is_public"]
        d['links'] = util.image_to_links(image["id"])
        if image["properties"]:
            d['metadata'] = image['properties']
        else:
            d['metadata'] = {}
        d["is_snapshot"] = image["is_snapshot"]
    return d


@api.api_method("GET", user_required=True, logger=log)
def list_images(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('list_images detail=%s', detail)
    since = utils.isoparse(request.GET.get('changes-since'))
    with backend.PlanktonBackend(request.user_uniq) as b:
        images = b.list_images()
        if since:
            updated_since = lambda img: date_parse(img["updated_at"]) >= since
            images = ifilter(updated_since, images)
            if not images:
                return HttpResponse(status=304)

    images = sorted(images, key=lambda x: x['id'])
    reply = [image_to_dict(image, detail) for image in images]

    if request.serialization == 'xml':
        data = render_to_string('list_images.xml',
                                dict(images=reply, detail=detail))
    else:
        data = json.dumps(dict(images=reply))

    return HttpResponse(data, status=200)


@api.api_method('POST', user_required=True, logger=log)
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

    raise faults.NotImplemented('Not supported.')


@api.api_method('GET', user_required=True, logger=log)
def get_image_details(request, image_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)

    log.debug('get_image_details %s', image_id)
    with backend.PlanktonBackend(request.user_uniq) as b:
        image = b.get_image(image_id)
    reply = image_to_dict(image)

    if request.serialization == 'xml':
        data = render_to_string('image.xml', dict(image=reply))
    else:
        data = json.dumps(dict(image=reply))

    return HttpResponse(data, status=200)


@api.api_method('DELETE', user_required=True, logger=log)
def delete_image(request, image_id):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       overLimit (413)

    log.info('delete_image %s', image_id)
    with backend.PlanktonBackend(request.user_uniq) as b:
        b.unregister(image_id)
    log.info('User %s deleted image %s', request.user_uniq, image_id)
    return HttpResponse(status=204)


@api.api_method('GET', user_required=True, logger=log)
def list_metadata(request, image_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('list_image_metadata %s', image_id)
    with backend.PlanktonBackend(request.user_uniq) as b:
        image = b.get_image(image_id)
    metadata = image['properties']
    return util.render_metadata(request, metadata, use_values=False,
                                status=200)


@api.api_method('POST', user_required=True, logger=log)
def update_metadata(request, image_id):
    # Normal Response Code: 201
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       overLimit (413)

    req = utils.get_json_body(request)
    log.info('update_image_metadata %s %s', image_id, req)
    with backend.PlanktonBackend(request.user_uniq) as b:
        image = b.get_image(image_id)
        try:
            metadata = req['metadata']
            assert isinstance(metadata, dict)
        except (KeyError, AssertionError):
            raise faults.BadRequest('Malformed request.')

        properties = image['properties']
        properties.update(metadata)

        b.update_metadata(image_id, dict(properties=properties))

    return util.render_metadata(request, properties, status=201)


@api.api_method('GET', user_required=True, logger=log)
def get_metadata_item(request, image_id, key):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('get_image_metadata_item %s %s', image_id, key)
    with backend.PlanktonBackend(request.user_uniq) as b:
        image = b.get_image(image_id)
    val = image['properties'].get(key)
    if val is None:
        raise faults.ItemNotFound('Metadata key not found.')
    return util.render_meta(request, {key: val}, status=200)


@api.api_method('PUT', user_required=True, logger=log)
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

    req = utils.get_json_body(request)
    log.info('create_image_metadata_item %s %s %s', image_id, key, req)
    try:
        metadict = req['meta']
        assert isinstance(metadict, dict)
        assert len(metadict) == 1
        assert key in metadict
    except (KeyError, AssertionError):
        raise faults.BadRequest('Malformed request.')

    val = metadict[key]
    with backend.PlanktonBackend(request.user_uniq) as b:
        image = b.get_image(image_id)
        properties = image['properties']
        properties[key] = val

        b.update_metadata(image_id, dict(properties=properties))

    return util.render_meta(request, {key: val}, status=201)


@api.api_method('DELETE', user_required=True, logger=log)
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
    with backend.PlanktonBackend(request.user_uniq) as b:
        image = b.get_image(image_id)
        properties = image['properties']
        properties.pop(key, None)

        b.update_metadata(image_id, dict(properties=properties))

    return HttpResponse(status=204)
