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

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from snf_django.lib import api
from snf_django.lib.api import faults

from pithos.api.settings import UNSAFE_DOMAIN, UPDATE_MD5
from pithos.api.util import (put_object_headers, update_manifest_meta,
                             validate_modification_preconditions,
                             validate_matching_preconditions,
                             object_data_response, api_method,
                             split_container_object_string, restrict_to_host)

import logging
logger = logging.getLogger(__name__)


@csrf_exempt
@restrict_to_host(UNSAFE_DOMAIN)
def public_demux(request, v_public):
    if request.method == 'HEAD':
        return public_meta(request, v_public)
    elif request.method == 'GET':
        return public_read(request, v_public)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['HEAD',
                                                           'GET'])


@api_method(http_method="HEAD", token_required=False, user_required=False,
            logger=logger)
def public_meta(request, v_public):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500),
    #                       itemNotFound (404),
    #                       badRequest (400)

    request.user_uniq = None
    try:
        v_account, v_container, v_object = request.backend.get_public(
            request.user_uniq,
            v_public)
        meta = request.backend.get_object_meta(request.user_uniq, v_account,
                                               v_container, v_object, 'pithos')
        public = request.backend.get_object_public(
            request.user_uniq, v_account,
            v_container, v_object)
    except:
        raise faults.ItemNotFound('Object does not exist')

    if not public:
        raise faults.ItemNotFound('Object does not exist')
    update_manifest_meta(request, v_account, meta)

    response = HttpResponse(status=200)
    put_object_headers(response, meta, True)
    return response


@api_method(http_method="GET", token_required=False, user_required=False,
            logger=logger)
def public_read(request, v_public):
    # Normal Response Codes: 200, 206
    # Error Response Codes: internalServerError (500),
    #                       rangeNotSatisfiable (416),
    #                       preconditionFailed (412),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       notModified (304)

    request.user_uniq = None
    try:
        v_account, v_container, v_object = request.backend.get_public(
            request.user_uniq,
            v_public)
        meta = request.backend.get_object_meta(request.user_uniq, v_account,
                                               v_container, v_object, 'pithos')
        public = request.backend.get_object_public(
            request.user_uniq, v_account,
            v_container, v_object)
    except:
        raise faults.ItemNotFound('Object does not exist')

    if not public:
        raise faults.ItemNotFound('Object does not exist')
    update_manifest_meta(request, v_account, meta)

    # Evaluate conditions.
    validate_modification_preconditions(request, meta)
    try:
        validate_matching_preconditions(request, meta)
    except faults.NotModified:
        response = HttpResponse(status=304)
        response['ETag'] = meta['hash'] if not UPDATE_MD5 else meta['checksum']
        return response

    sizes = []
    hashmaps = []
    if 'X-Object-Manifest' in meta:
        try:
            src_container, src_name = split_container_object_string(
                '/' + meta['X-Object-Manifest'])
            objects = request.backend.list_objects(
                request.user_uniq, v_account,
                src_container, prefix=src_name, virtual=False)
        except:
            raise faults.ItemNotFound('Object does not exist')

        try:
            for x in objects:
                _, s, h = request.backend.get_object_hashmap(request.user_uniq,
                                                             v_account,
                                                             src_container,
                                                             x[0], x[1])
                sizes.append(s)
                hashmaps.append(h)
        except:
            raise faults.ItemNotFound('Object does not exist')
    else:
        try:
            _, s, h = request.backend.get_object_hashmap(
                request.user_uniq, v_account,
                v_container, v_object)
            sizes.append(s)
            hashmaps.append(h)
        except:
            raise faults.ItemNotFound('Object does not exist')
    return object_data_response(request, sizes, hashmaps, meta, True)
