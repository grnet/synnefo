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

from xml.dom import minidom

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json
from django.utils.http import parse_etags
from django.utils.encoding import smart_str
from django.views.decorators.csrf import csrf_exempt

from synnefo.lib.astakos import get_user, get_uuids as _get_uuids

from snf_django.lib import api
from snf_django.lib.api import faults

from pithos.api.util import (
    json_encode_decimal, rename_meta_key, format_header_key,
    printable_header_dict, get_account_headers, put_account_headers,
    get_container_headers, put_container_headers, get_object_headers,
    put_object_headers, update_manifest_meta, update_sharing_meta,
    update_public_meta, validate_modification_preconditions,
    validate_matching_preconditions, split_container_object_string,
    copy_or_move_object, get_int_parameter, get_content_length,
    get_content_range, socket_read_iterator, SaveToBackendHandler,
    object_data_response, put_object_block, hashmap_md5, simple_list_response,
    api_method, is_uuid,
    retrieve_uuid, retrieve_displayname, retrieve_uuids, retrieve_displaynames,
    get_pithos_usage
)

from pithos.api.settings import (UPDATE_MD5, TRANSLATE_UUIDS,
                                 SERVICE_TOKEN, AUTHENTICATION_URL,
                                 AUTHENTICATION_USERS)

from pithos.backends.base import (
    NotAllowedError, QuotaError, ContainerNotEmpty, ItemNotExists,
    VersionNotExists, ContainerExists)

from pithos.backends.filter import parse_filters

import hashlib

import logging
logger = logging.getLogger(__name__)


def get_uuids(names):
    try:
        uuids = _get_uuids(SERVICE_TOKEN, names,
                           url=AUTHENTICATION_URL.replace(
                                            'im/authenticate',
                                            'service/api/user_catalogs'),
                           override_users=AUTHENTICATION_USERS)
    except Exception, e:
        logger.exception(e)
        return {}

    return uuids


@csrf_exempt
def top_demux(request):
    if request.method == 'GET':
        try:
            request.GET['X-Auth-Token']
        except KeyError:
            try:
                request.META['HTTP_X_AUTH_TOKEN']
            except KeyError:
                return authenticate(request)
        return account_list(request)
    else:
        return api.method_not_allowed(request)


@csrf_exempt
def account_demux(request, v_account):
    if TRANSLATE_UUIDS:
        if not is_uuid(v_account):
            uuids = get_uuids([v_account])
            if not uuids or not v_account in uuids:
                return HttpResponse(status=404)
            v_account = uuids[v_account]

    if request.method == 'HEAD':
        return account_meta(request, v_account)
    elif request.method == 'POST':
        return account_update(request, v_account)
    elif request.method == 'GET':
        return container_list(request, v_account)
    else:
        return api.method_not_allowed(request)


@csrf_exempt
def container_demux(request, v_account, v_container):
    if TRANSLATE_UUIDS:
        if not is_uuid(v_account):
            uuids = get_uuids([v_account])
            if not uuids or not v_account in uuids:
                return HttpResponse(status=404)
            v_account = uuids[v_account]

    if request.method == 'HEAD':
        return container_meta(request, v_account, v_container)
    elif request.method == 'PUT':
        return container_create(request, v_account, v_container)
    elif request.method == 'POST':
        return container_update(request, v_account, v_container)
    elif request.method == 'DELETE':
        return container_delete(request, v_account, v_container)
    elif request.method == 'GET':
        return object_list(request, v_account, v_container)
    else:
        return api.method_not_allowed(request)


@csrf_exempt
def object_demux(request, v_account, v_container, v_object):
    # Helper to avoid placing the token in the URL when loading objects from a browser.
    if TRANSLATE_UUIDS:
        if not is_uuid(v_account):
            uuids = get_uuids([v_account])
            if not uuids or not v_account in uuids:
                return HttpResponse(status=404)
            v_account = uuids[v_account]

    if request.method == 'HEAD':
        return object_meta(request, v_account, v_container, v_object)
    elif request.method == 'GET':
        return object_read(request, v_account, v_container, v_object)
    elif request.method == 'PUT':
        return object_write(request, v_account, v_container, v_object)
    elif request.method == 'COPY':
        return object_copy(request, v_account, v_container, v_object)
    elif request.method == 'MOVE':
        return object_move(request, v_account, v_container, v_object)
    elif request.method == 'POST':
        if request.META.get('CONTENT_TYPE', '').startswith('multipart/form-data'):
            return object_write_form(request, v_account, v_container, v_object)
        return object_update(request, v_account, v_container, v_object)
    elif request.method == 'DELETE':
        return object_delete(request, v_account, v_container, v_object)
    else:
        return api.method_not_allowed(request)


@api_method('GET', user_required=False, logger=logger)
def authenticate(request):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500),
    #                       forbidden (403),
    #                       badRequest (400)

    x_auth_user = request.META.get('HTTP_X_AUTH_USER')
    x_auth_key = request.META.get('HTTP_X_AUTH_KEY')
    if not x_auth_user or not x_auth_key:
        raise faults.BadRequest('Missing X-Auth-User or X-Auth-Key header')
    response = HttpResponse(status=204)

    uri = request.build_absolute_uri()
    if '?' in uri:
        uri = uri[:uri.find('?')]

    response['X-Auth-Token'] = x_auth_key
    response['X-Storage-Url'] = uri + ('' if uri.endswith('/')
                                       else '/') + x_auth_user
    return response


@api_method('GET', format_allowed=True, user_required=True, logger=logger)
def account_list(request):
    # Normal Response Codes: 200, 204
    # Error Response Codes: internalServerError (500),
    #                       badRequest (400)
    response = HttpResponse()

    marker = request.GET.get('marker')
    limit = get_int_parameter(request.GET.get('limit'))
    if not limit:
        limit = 10000

    accounts = request.backend.list_accounts(request.user_uniq, marker, limit)

    if request.serialization == 'text':
        if TRANSLATE_UUIDS:
            accounts = retrieve_displaynames(
                    getattr(request, 'token', None), accounts)
        if len(accounts) == 0:
            # The cloudfiles python bindings expect 200 if json/xml.
            response.status_code = 204
            return response
        response.status_code = 200
        response.content = '\n'.join(accounts) + '\n'
        return response

    account_meta = []
    for x in accounts:
        if x == request.user_uniq:
            continue
        usage = get_pithos_usage(request.x_auth_token)
        try:
            meta = request.backend.get_account_meta(
                request.user_uniq, x, 'pithos', include_user_defined=False,
                external_quota=usage)
            groups = request.backend.get_account_groups(request.user_uniq, x)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        else:
            rename_meta_key(meta, 'modified', 'last_modified')
            rename_meta_key(
                meta, 'until_timestamp', 'x_account_until_timestamp')
            if groups:
                meta['X-Account-Group'] = printable_header_dict(
                    dict([(k, ','.join(v)) for k, v in groups.iteritems()]))
            account_meta.append(printable_header_dict(meta))

    if TRANSLATE_UUIDS:
        uuids = list(d['name'] for d in account_meta)
        catalog = retrieve_displaynames(
                getattr(request, 'token', None), uuids, return_dict=True)
        for meta in account_meta:
            meta['name'] = catalog.get(meta.get('name'))

    if request.serialization == 'xml':
        data = render_to_string('accounts.xml', {'accounts': account_meta})
    elif request.serialization == 'json':
        data = json.dumps(account_meta)
    response.status_code = 200
    response.content = data
    return response


@api_method('HEAD', user_required=True, logger=logger)
def account_meta(request, v_account):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500),
    #                       forbidden (403),
    #                       badRequest (400)

    until = get_int_parameter(request.GET.get('until'))
    usage = get_pithos_usage(request.x_auth_token)
    try:
        meta = request.backend.get_account_meta(
            request.user_uniq, v_account, 'pithos', until,
            external_quota=usage)
        groups = request.backend.get_account_groups(
            request.user_uniq, v_account)

        if TRANSLATE_UUIDS:
            for k in groups:
                groups[k] = retrieve_displaynames(
                        getattr(request, 'token', None), groups[k])
        policy = request.backend.get_account_policy(
            request.user_uniq, v_account, external_quota=usage)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')

    validate_modification_preconditions(request, meta)

    response = HttpResponse(status=204)
    put_account_headers(response, meta, groups, policy)
    return response


@api_method('POST', user_required=True, logger=logger)
def account_update(request, v_account):
    # Normal Response Codes: 202
    # Error Response Codes: internalServerError (500),
    #                       forbidden (403),
    #                       badRequest (400)

    meta, groups = get_account_headers(request)
    for k in groups:
        if TRANSLATE_UUIDS:
            try:
                groups[k] = retrieve_uuids(
                        getattr(request, 'token', None),
                        groups[k],
                        fail_silently=False)
            except ItemNotExists, e:
                raise faults.BadRequest(
                        'Bad X-Account-Group header value: %s' % e)
        else:
            try:
                retrieve_displaynames(
                    getattr(request, 'token', None),
                    groups[k],
                    fail_silently=False)
            except ItemNotExists, e:
                raise faults.BadRequest(
                        'Bad X-Account-Group header value: %s' % e)
    replace = True
    if 'update' in request.GET:
        replace = False
    if groups:
        try:
            request.backend.update_account_groups(request.user_uniq, v_account,
                                                  groups, replace)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ValueError:
            raise faults.BadRequest('Invalid groups header')
    if meta or replace:
        try:
            request.backend.update_account_meta(request.user_uniq, v_account,
                                                'pithos', meta, replace)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
    return HttpResponse(status=202)


@api_method('GET', format_allowed=True, user_required=True, logger=logger)
def container_list(request, v_account):
    # Normal Response Codes: 200, 204
    # Error Response Codes: internalServerError (500),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)

    until = get_int_parameter(request.GET.get('until'))
    usage = get_pithos_usage(request.x_auth_token)
    try:
        meta = request.backend.get_account_meta(
            request.user_uniq, v_account, 'pithos', until,
            external_quota=usage)
        groups = request.backend.get_account_groups(
            request.user_uniq, v_account)
        policy = request.backend.get_account_policy(
            request.user_uniq, v_account, external_quota=usage)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')

    validate_modification_preconditions(request, meta)

    response = HttpResponse()
    put_account_headers(response, meta, groups, policy)

    marker = request.GET.get('marker')
    limit = get_int_parameter(request.GET.get('limit'))
    if not limit:
        limit = 10000

    shared = False
    if 'shared' in request.GET:
        shared = True
    public = False
    if request.user_uniq == v_account and 'public' in request.GET:
        public = True

    try:
        containers = request.backend.list_containers(
            request.user_uniq, v_account,
            marker, limit, shared, until, public)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except NameError:
        containers = []

    if request.serialization == 'text':
        if len(containers) == 0:
            # The cloudfiles python bindings expect 200 if json/xml.
            response.status_code = 204
            return response
        response.status_code = 200
        response.content = '\n'.join(containers) + '\n'
        return response

    container_meta = []
    for x in containers:
        try:
            meta = request.backend.get_container_meta(
                request.user_uniq, v_account,
                x, 'pithos', until, include_user_defined=False)
            policy = request.backend.get_container_policy(request.user_uniq,
                                                          v_account, x)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except NameError:
            pass
        else:
            rename_meta_key(meta, 'modified', 'last_modified')
            rename_meta_key(
                meta, 'until_timestamp', 'x_container_until_timestamp')
            if policy:
                meta['X-Container-Policy'] = printable_header_dict(
                    dict([(k, v) for k, v in policy.iteritems()]))
            container_meta.append(printable_header_dict(meta))
    if request.serialization == 'xml':
        data = render_to_string('containers.xml', {'account':
                                v_account, 'containers': container_meta})
    elif request.serialization == 'json':
        data = json.dumps(container_meta)
    response.status_code = 200
    response.content = data
    return response


@api_method('HEAD', user_required=True, logger=logger)
def container_meta(request, v_account, v_container):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)

    until = get_int_parameter(request.GET.get('until'))
    try:
        meta = request.backend.get_container_meta(request.user_uniq, v_account,
                                                  v_container, 'pithos', until)
        meta['object_meta'] = request.backend.list_container_meta(request.user_uniq,
                                                                  v_account, v_container, 'pithos', until)
        policy = request.backend.get_container_policy(
            request.user_uniq, v_account,
            v_container)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ItemNotExists:
        raise faults.ItemNotFound('Container does not exist')

    validate_modification_preconditions(request, meta)

    response = HttpResponse(status=204)
    put_container_headers(request, response, meta, policy)
    return response


@api_method('PUT', user_required=True, logger=logger)
def container_create(request, v_account, v_container):
    # Normal Response Codes: 201, 202
    # Error Response Codes: internalServerError (500),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)

    meta, policy = get_container_headers(request)

    try:
        request.backend.put_container(
            request.user_uniq, v_account, v_container, policy)
        ret = 201
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ValueError:
        raise faults.BadRequest('Invalid policy header')
    except ContainerExists:
        ret = 202

    if ret == 202 and policy:
        try:
            request.backend.update_container_policy(
                request.user_uniq, v_account,
                v_container, policy, replace=False)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Container does not exist')
        except ValueError:
            raise faults.BadRequest('Invalid policy header')
    if meta:
        try:
            request.backend.update_container_meta(request.user_uniq, v_account,
                                                  v_container, 'pithos', meta, replace=False)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Container does not exist')

    return HttpResponse(status=ret)


@api_method('POST', format_allowed=True, user_required=True, logger=logger)
def container_update(request, v_account, v_container):
    # Normal Response Codes: 202
    # Error Response Codes: internalServerError (500),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)

    meta, policy = get_container_headers(request)
    replace = True
    if 'update' in request.GET:
        replace = False
    if policy:
        try:
            request.backend.update_container_policy(
                request.user_uniq, v_account,
                v_container, policy, replace)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Container does not exist')
        except ValueError:
            raise faults.BadRequest('Invalid policy header')
    if meta or replace:
        try:
            request.backend.update_container_meta(request.user_uniq, v_account,
                                                  v_container, 'pithos', meta, replace)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Container does not exist')

    content_length = -1
    if request.META.get('HTTP_TRANSFER_ENCODING') != 'chunked':
        content_length = get_int_parameter(
            request.META.get('CONTENT_LENGTH', 0))
    content_type = request.META.get('CONTENT_TYPE')
    hashmap = []
    if content_type and content_type == 'application/octet-stream' and content_length != 0:
        for data in socket_read_iterator(request, content_length,
                                         request.backend.block_size):
            # TODO: Raise 408 (Request Timeout) if this takes too long.
            # TODO: Raise 499 (Client Disconnect) if a length is defined and we stop before getting this much data.
            hashmap.append(request.backend.put_block(data))

    response = HttpResponse(status=202)
    if hashmap:
        response.content = simple_list_response(request, hashmap)
    return response


@api_method('DELETE', user_required=True, logger=logger)
def container_delete(request, v_account, v_container):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500),
    #                       conflict (409),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)
    #                       requestentitytoolarge (413)

    until = get_int_parameter(request.GET.get('until'))

    delimiter = request.GET.get('delimiter')

    try:
        request.backend.delete_container(
            request.user_uniq, v_account, v_container,
            until, delimiter=delimiter)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ItemNotExists:
        raise faults.ItemNotFound('Container does not exist')
    except ContainerNotEmpty:
        raise faults.Conflict('Container is not empty')
    except QuotaError, e:
        raise faults.RequestEntityTooLarge('Quota error: %s' % e)
    return HttpResponse(status=204)


@api_method('GET', format_allowed=True, user_required=True, logger=logger)
def object_list(request, v_account, v_container):
    # Normal Response Codes: 200, 204
    # Error Response Codes: internalServerError (500),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)

    until = get_int_parameter(request.GET.get('until'))
    try:
        meta = request.backend.get_container_meta(request.user_uniq, v_account,
                                                  v_container, 'pithos', until)
        meta['object_meta'] = request.backend.list_container_meta(request.user_uniq,
                                                                  v_account, v_container, 'pithos', until)
        policy = request.backend.get_container_policy(
            request.user_uniq, v_account,
            v_container)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ItemNotExists:
        raise faults.ItemNotFound('Container does not exist')

    validate_modification_preconditions(request, meta)

    response = HttpResponse()
    put_container_headers(request, response, meta, policy)

    path = request.GET.get('path')
    prefix = request.GET.get('prefix')
    delimiter = request.GET.get('delimiter')

    # Path overrides prefix and delimiter.
    virtual = True
    if path:
        prefix = path
        delimiter = '/'
        virtual = False

    # Naming policy.
    if prefix and delimiter and not prefix.endswith(delimiter):
        prefix = prefix + delimiter
    if not prefix:
        prefix = ''
    prefix = prefix.lstrip('/')

    marker = request.GET.get('marker')
    limit = get_int_parameter(request.GET.get('limit'))
    if not limit:
        limit = 10000

    keys = request.GET.get('meta')
    if keys:
        keys = [smart_str(x.strip()) for x in keys.split(',')
                if x.strip() != '']
        included, excluded, opers = parse_filters(keys)
        keys = []
        keys += [format_header_key('X-Object-Meta-' + x) for x in included]
        keys += ['!' + format_header_key('X-Object-Meta-' + x)
                 for x in excluded]
        keys += ['%s%s%s' % (format_header_key(
            'X-Object-Meta-' + k), o, v) for k, o, v in opers]
    else:
        keys = []

    shared = False
    if 'shared' in request.GET:
        shared = True

    public_requested = 'public' in request.GET
    public_granted = public_requested and request.user_uniq == v_account

    if request.serialization == 'text':
        try:
            objects = request.backend.list_objects(
                request.user_uniq, v_account,
                v_container, prefix, delimiter, marker,
                limit, virtual, 'pithos', keys, shared,
                until, None, public_granted)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Container does not exist')

        if len(objects) == 0:
            # The cloudfiles python bindings expect 200 if json/xml.
            response.status_code = 204
            return response
        response.status_code = 200
        response.content = '\n'.join([x[0] for x in objects]) + '\n'
        return response

    try:
        objects = request.backend.list_object_meta(
            request.user_uniq, v_account,
            v_container, prefix, delimiter, marker,
            limit, virtual, 'pithos', keys, shared, until, None, public_granted)
        object_permissions = {}
        object_public = {}
        if until is None:
            name = '/'.join((v_account, v_container, ''))
            name_idx = len(name)
            for x in request.backend.list_object_permissions(request.user_uniq,
                                                             v_account, v_container, prefix):

                # filter out objects which are not under the container
                if name != x[:name_idx]:
                    continue

                object = x[name_idx:]
                object_permissions[object] = request.backend.get_object_permissions(
                    request.user_uniq, v_account, v_container, object)

            if public_granted:
                for k, v in request.backend.list_object_public(
                        request.user_uniq, v_account,
                        v_container, prefix).iteritems():
                    object_public[k[name_idx:]] = v
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ItemNotExists:
        raise faults.ItemNotFound('Container does not exist')

    object_meta = []
    for meta in objects:
        if TRANSLATE_UUIDS:
            modified_by = meta.get('modified_by')
            if modified_by:
                l = retrieve_displaynames(
                        getattr(request, 'token', None), [meta['modified_by']])
                if l is not None and len(l) == 1:
                    meta['modified_by'] = l[0]

        if len(meta) == 1:
            # Virtual objects/directories.
            object_meta.append(meta)
        else:
            rename_meta_key(
                meta, 'hash', 'x_object_hash')  # Will be replaced by checksum.
            rename_meta_key(meta, 'checksum', 'hash')
            rename_meta_key(meta, 'type', 'content_type')
            rename_meta_key(meta, 'uuid', 'x_object_uuid')
            if until is not None and 'modified' in meta:
                del(meta['modified'])
            else:
                rename_meta_key(meta, 'modified', 'last_modified')
            rename_meta_key(meta, 'modified_by', 'x_object_modified_by')
            rename_meta_key(meta, 'version', 'x_object_version')
            rename_meta_key(
                meta, 'version_timestamp', 'x_object_version_timestamp')
            permissions = object_permissions.get(meta['name'], None)
            if permissions:
                update_sharing_meta(request, permissions, v_account,
                                    v_container, meta['name'], meta)
            public_url = object_public.get(meta['name'], None)
            if public_granted:
                update_public_meta(public_url, meta)
            object_meta.append(printable_header_dict(meta))

    if request.serialization == 'xml':
        data = render_to_string(
            'objects.xml', {'container': v_container, 'objects': object_meta})
    elif request.serialization == 'json':
        data = json.dumps(object_meta, default=json_encode_decimal)
    response.status_code = 200
    response.content = data
    return response


@api_method('HEAD', user_required=True, logger=logger)
def object_meta(request, v_account, v_container, v_object):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)

    version = request.GET.get('version')
    try:
        meta = request.backend.get_object_meta(request.user_uniq, v_account,
                                               v_container, v_object, 'pithos', version)
        if version is None:
            permissions = request.backend.get_object_permissions(
                request.user_uniq,
                v_account, v_container, v_object)
            public = request.backend.get_object_public(
                request.user_uniq, v_account,
                v_container, v_object)
        else:
            permissions = None
            public = None
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ItemNotExists:
        raise faults.ItemNotFound('Object does not exist')
    except VersionNotExists:
        raise faults.ItemNotFound('Version does not exist')

    update_manifest_meta(request, v_account, meta)
    update_sharing_meta(
        request, permissions, v_account, v_container, v_object, meta)
    if request.user_uniq == v_account:
        update_public_meta(public, meta)

    # Evaluate conditions.
    validate_modification_preconditions(request, meta)
    try:
        validate_matching_preconditions(request, meta)
    except faults.NotModified:
        response = HttpResponse(status=304)
        response['ETag'] = meta['checksum']
        return response

    response = HttpResponse(status=200)
    put_object_headers(response, meta, token=getattr(request, 'token', None))
    return response


@api_method('GET', format_allowed=True, user_required=True, logger=logger)
def object_read(request, v_account, v_container, v_object):
    # Normal Response Codes: 200, 206
    # Error Response Codes: internalServerError (500),
    #                       rangeNotSatisfiable (416),
    #                       preconditionFailed (412),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400),
    #                       notModified (304)

    version = request.GET.get('version')

    # Reply with the version list. Do this first, as the object may be deleted.
    if version == 'list':
        if request.serialization == 'text':
            raise faults.BadRequest('No format specified for version list.')

        try:
            v = request.backend.list_versions(request.user_uniq, v_account,
                                              v_container, v_object)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Object does not exist')
        d = {'versions': v}
        if request.serialization == 'xml':
            d['object'] = v_object
            data = render_to_string('versions.xml', d)
        elif request.serialization == 'json':
            data = json.dumps(d, default=json_encode_decimal)

        response = HttpResponse(data, status=200)
        response['Content-Length'] = len(data)
        return response

    try:
        meta = request.backend.get_object_meta(request.user_uniq, v_account,
                                               v_container, v_object, 'pithos', version)
        if version is None:
            permissions = request.backend.get_object_permissions(
                request.user_uniq,
                v_account, v_container, v_object)
            public = request.backend.get_object_public(
                request.user_uniq, v_account,
                v_container, v_object)
        else:
            permissions = None
            public = None
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ItemNotExists:
        raise faults.ItemNotFound('Object does not exist')
    except VersionNotExists:
        raise faults.ItemNotFound('Version does not exist')

    update_manifest_meta(request, v_account, meta)
    update_sharing_meta(
        request, permissions, v_account, v_container, v_object, meta)
    if request.user_uniq == v_account:
        update_public_meta(public, meta)

    # Evaluate conditions.
    validate_modification_preconditions(request, meta)
    try:
        validate_matching_preconditions(request, meta)
    except faults.NotModified:
        response = HttpResponse(status=304)
        response['ETag'] = meta['checksum']
        return response

    hashmap_reply = False
    if 'hashmap' in request.GET and request.serialization != 'text':
        hashmap_reply = True

    sizes = []
    hashmaps = []
    if 'X-Object-Manifest' in meta and not hashmap_reply:
        try:
            src_container, src_name = split_container_object_string(
                '/' + meta['X-Object-Manifest'])
            objects = request.backend.list_objects(
                request.user_uniq, v_account,
                src_container, prefix=src_name, virtual=False)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ValueError:
            raise faults.BadRequest('Invalid X-Object-Manifest header')
        except ItemNotExists:
            raise faults.ItemNotFound('Container does not exist')

        try:
            for x in objects:
                s, h = request.backend.get_object_hashmap(request.user_uniq,
                                                          v_account, src_container, x[0], x[1])
                sizes.append(s)
                hashmaps.append(h)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Object does not exist')
        except VersionNotExists:
            raise faults.ItemNotFound('Version does not exist')
    else:
        try:
            s, h = request.backend.get_object_hashmap(
                request.user_uniq, v_account,
                v_container, v_object, version)
            sizes.append(s)
            hashmaps.append(h)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Object does not exist')
        except VersionNotExists:
            raise faults.ItemNotFound('Version does not exist')

    # Reply with the hashmap.
    if hashmap_reply:
        size = sum(sizes)
        hashmap = sum(hashmaps, [])
        d = {
            'block_size': request.backend.block_size,
            'block_hash': request.backend.hash_algorithm,
            'bytes': size,
            'hashes': hashmap}
        if request.serialization == 'xml':
            d['object'] = v_object
            data = render_to_string('hashes.xml', d)
        elif request.serialization == 'json':
            data = json.dumps(d)

        response = HttpResponse(data, status=200)
        put_object_headers(
                response, meta, token=getattr(request, 'token', None))
        response['Content-Length'] = len(data)
        return response

    request.serialization = 'text'  # Unset.
    return object_data_response(request, sizes, hashmaps, meta)


@api_method('PUT', format_allowed=True, user_required=True, logger=logger)
def object_write(request, v_account, v_container, v_object):
    # Normal Response Codes: 201
    # Error Response Codes: internalServerError (500),
    #                       unprocessableEntity (422),
    #                       lengthRequired (411),
    #                       conflict (409),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)
    #                       requestentitytoolarge (413)

    # Evaluate conditions.
    if request.META.get('HTTP_IF_MATCH') or request.META.get('HTTP_IF_NONE_MATCH'):
        try:
            meta = request.backend.get_object_meta(
                request.user_uniq, v_account,
                v_container, v_object, 'pithos')
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except NameError:
            meta = {}
        validate_matching_preconditions(request, meta)

    copy_from = request.META.get('HTTP_X_COPY_FROM')
    move_from = request.META.get('HTTP_X_MOVE_FROM')
    if copy_from or move_from:
        delimiter = request.GET.get('delimiter')
        content_length = get_content_length(request)  # Required by the API.

        src_account = request.META.get('HTTP_X_SOURCE_ACCOUNT')

        if not src_account:
            src_account = request.user_uniq
        else:
            if TRANSLATE_UUIDS:
                try:
                    src_account = retrieve_uuid(getattr(request, 'token', None),
                                                src_account)
                except ItemNotExists:
                    faults.ItemNotFound('Invalid source account')

        if move_from:
            try:
                src_container, src_name = split_container_object_string(
                    move_from)
            except ValueError:
                raise faults.BadRequest('Invalid X-Move-From header')
            version_id = copy_or_move_object(
                request, src_account, src_container, src_name,
                v_account, v_container, v_object, move=True, delimiter=delimiter)
        else:
            try:
                src_container, src_name = split_container_object_string(
                    copy_from)
            except ValueError:
                raise faults.BadRequest('Invalid X-Copy-From header')
            version_id = copy_or_move_object(
                request, src_account, src_container, src_name,
                v_account, v_container, v_object, move=False, delimiter=delimiter)
        response = HttpResponse(status=201)
        response['X-Object-Version'] = version_id
        return response

    content_type, meta, permissions, public = get_object_headers(request)
    content_length = -1
    if request.META.get('HTTP_TRANSFER_ENCODING') != 'chunked':
        content_length = get_content_length(request)
    # Should be BadRequest, but API says otherwise.
    if content_type is None:
        raise faults.LengthRequired('Missing Content-Type header')

    if 'hashmap' in request.GET:
        if request.serialization not in ('json', 'xml'):
            raise faults.BadRequest('Invalid hashmap format')

        data = ''
        for block in socket_read_iterator(request, content_length,
                                          request.backend.block_size):
            data = '%s%s' % (data, block)

        if request.serialization == 'json':
            d = json.loads(data)
            if not hasattr(d, '__getitem__'):
                raise faults.BadRequest('Invalid data formating')
            try:
                hashmap = d['hashes']
                size = int(d['bytes'])
            except:
                raise faults.BadRequest('Invalid data formatting')
        elif request.serialization == 'xml':
            try:
                xml = minidom.parseString(data)
                obj = xml.getElementsByTagName('object')[0]
                size = int(obj.attributes['bytes'].value)

                hashes = xml.getElementsByTagName('hash')
                hashmap = []
                for hash in hashes:
                    hashmap.append(hash.firstChild.data)
            except:
                raise faults.BadRequest('Invalid data formatting')

        checksum = ''  # Do not set to None (will copy previous value).
    else:
        md5 = hashlib.md5()
        size = 0
        hashmap = []
        for data in socket_read_iterator(request, content_length,
                                         request.backend.block_size):
            # TODO: Raise 408 (Request Timeout) if this takes too long.
            # TODO: Raise 499 (Client Disconnect) if a length is defined and we stop before getting this much data.
            size += len(data)
            hashmap.append(request.backend.put_block(data))
            md5.update(data)

        checksum = md5.hexdigest().lower()
        etag = request.META.get('HTTP_ETAG')
        if etag and parse_etags(etag)[0].lower() != checksum:
            raise faults.UnprocessableEntity('Object ETag does not match')

    try:
        version_id = request.backend.update_object_hashmap(request.user_uniq,
                                                           v_account, v_container, v_object, size, content_type,
                                                           hashmap, checksum, 'pithos', meta, True, permissions)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except IndexError, e:
        raise faults.Conflict(simple_list_response(request, e.data))
    except ItemNotExists:
        raise faults.ItemNotFound('Container does not exist')
    except ValueError:
        raise faults.BadRequest('Invalid sharing header')
    except QuotaError, e:
        raise faults.RequestEntityTooLarge('Quota error: %s' % e)
    if not checksum and UPDATE_MD5:
        # Update the MD5 after the hashmap, as there may be missing hashes.
        checksum = hashmap_md5(request.backend, hashmap, size)
        try:
            request.backend.update_object_checksum(request.user_uniq,
                                                   v_account, v_container, v_object, version_id, checksum)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
    if public is not None:
        try:
            request.backend.update_object_public(request.user_uniq, v_account,
                                                 v_container, v_object, public)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Object does not exist')

    response = HttpResponse(status=201)
    if checksum:
        response['ETag'] = checksum
    response['X-Object-Version'] = version_id
    return response


@api_method('POST', user_required=True, logger=logger)
def object_write_form(request, v_account, v_container, v_object):
    # Normal Response Codes: 201
    # Error Response Codes: internalServerError (500),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)
    #                       requestentitytoolarge (413)

    request.upload_handlers = [SaveToBackendHandler(request)]
    if 'X-Object-Data' not in request.FILES:
        raise faults.BadRequest('Missing X-Object-Data field')
    file = request.FILES['X-Object-Data']

    checksum = file.etag
    try:
        version_id = request.backend.update_object_hashmap(request.user_uniq,
                                                           v_account, v_container, v_object, file.size, file.content_type,
                                                           file.hashmap, checksum, 'pithos', {}, True)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ItemNotExists:
        raise faults.ItemNotFound('Container does not exist')
    except QuotaError, e:
        raise faults.RequestEntityTooLarge('Quota error: %s' % e)

    response = HttpResponse(status=201)
    response['ETag'] = checksum
    response['X-Object-Version'] = version_id
    response.content = checksum
    return response


@api_method('COPY', format_allowed=True, user_required=True, logger=logger)
def object_copy(request, v_account, v_container, v_object):
    # Normal Response Codes: 201
    # Error Response Codes: internalServerError (500),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)
    #                       requestentitytoolarge (413)

    dest_account = request.META.get('HTTP_DESTINATION_ACCOUNT')
    if not dest_account:
        dest_account = request.user_uniq
    dest_path = request.META.get('HTTP_DESTINATION')
    if not dest_path:
        raise faults.BadRequest('Missing Destination header')
    try:
        dest_container, dest_name = split_container_object_string(dest_path)
    except ValueError:
        raise faults.BadRequest('Invalid Destination header')

    # Evaluate conditions.
    if request.META.get('HTTP_IF_MATCH') or request.META.get('HTTP_IF_NONE_MATCH'):
        src_version = request.META.get('HTTP_X_SOURCE_VERSION')
        try:
            meta = request.backend.get_object_meta(
                request.user_uniq, v_account,
                v_container, v_object, 'pithos', src_version)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except (ItemNotExists, VersionNotExists):
            raise faults.ItemNotFound('Container or object does not exist')
        validate_matching_preconditions(request, meta)

    delimiter = request.GET.get('delimiter')

    version_id = copy_or_move_object(request, v_account, v_container, v_object,
                                     dest_account, dest_container, dest_name, move=False, delimiter=delimiter)
    response = HttpResponse(status=201)
    response['X-Object-Version'] = version_id
    return response


@api_method('MOVE', format_allowed=True, user_required=True, logger=logger)
def object_move(request, v_account, v_container, v_object):
    # Normal Response Codes: 201
    # Error Response Codes: internalServerError (500),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)
    #                       requestentitytoolarge (413)

    dest_account = request.META.get('HTTP_DESTINATION_ACCOUNT')
    if not dest_account:
        dest_account = request.user_uniq
    dest_path = request.META.get('HTTP_DESTINATION')
    if not dest_path:
        raise faults.BadRequest('Missing Destination header')
    try:
        dest_container, dest_name = split_container_object_string(dest_path)
    except ValueError:
        raise faults.BadRequest('Invalid Destination header')

    # Evaluate conditions.
    if request.META.get('HTTP_IF_MATCH') or request.META.get('HTTP_IF_NONE_MATCH'):
        try:
            meta = request.backend.get_object_meta(
                request.user_uniq, v_account,
                v_container, v_object, 'pithos')
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Container or object does not exist')
        validate_matching_preconditions(request, meta)

    delimiter = request.GET.get('delimiter')

    version_id = copy_or_move_object(request, v_account, v_container, v_object,
                                     dest_account, dest_container, dest_name, move=True, delimiter=delimiter)
    response = HttpResponse(status=201)
    response['X-Object-Version'] = version_id
    return response


@api_method('POST', format_allowed=True, user_required=True, logger=logger)
def object_update(request, v_account, v_container, v_object):
    # Normal Response Codes: 202, 204
    # Error Response Codes: internalServerError (500),
    #                       conflict (409),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)

    content_type, meta, permissions, public = get_object_headers(request)

    try:
        prev_meta = request.backend.get_object_meta(
            request.user_uniq, v_account,
            v_container, v_object, 'pithos')
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ItemNotExists:
        raise faults.ItemNotFound('Object does not exist')

    # Evaluate conditions.
    if request.META.get('HTTP_IF_MATCH') or request.META.get('HTTP_IF_NONE_MATCH'):
        validate_matching_preconditions(request, prev_meta)

    replace = True
    if 'update' in request.GET:
        replace = False

    # A Content-Type or X-Source-Object header indicates data updates.
    src_object = request.META.get('HTTP_X_SOURCE_OBJECT')
    if (not content_type or content_type != 'application/octet-stream') and not src_object:
        response = HttpResponse(status=202)

        # Do permissions first, as it may fail easier.
        if permissions is not None:
            try:
                request.backend.update_object_permissions(request.user_uniq,
                                                          v_account, v_container, v_object, permissions)
            except NotAllowedError:
                raise faults.Forbidden('Not allowed')
            except ItemNotExists:
                raise faults.ItemNotFound('Object does not exist')
            except ValueError:
                raise faults.BadRequest('Invalid sharing header')
        if public is not None:
            try:
                request.backend.update_object_public(
                    request.user_uniq, v_account,
                    v_container, v_object, public)
            except NotAllowedError:
                raise faults.Forbidden('Not allowed')
            except ItemNotExists:
                raise faults.ItemNotFound('Object does not exist')
        if meta or replace:
            try:
                version_id = request.backend.update_object_meta(
                    request.user_uniq,
                    v_account, v_container, v_object, 'pithos', meta, replace)
            except NotAllowedError:
                raise faults.Forbidden('Not allowed')
            except ItemNotExists:
                raise faults.ItemNotFound('Object does not exist')
            response['X-Object-Version'] = version_id

        return response

    # Single range update. Range must be in Content-Range.
    # Based on: http://code.google.com/p/gears/wiki/ContentRangePostProposal
    # (with the addition that '*' is allowed for the range - will append).
    content_range = request.META.get('HTTP_CONTENT_RANGE')
    if not content_range:
        raise faults.BadRequest('Missing Content-Range header')
    ranges = get_content_range(request)
    if not ranges:
        raise faults.RangeNotSatisfiable('Invalid Content-Range header')

    try:
        size, hashmap = request.backend.get_object_hashmap(request.user_uniq,
                                                           v_account, v_container, v_object)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ItemNotExists:
        raise faults.ItemNotFound('Object does not exist')

    offset, length, total = ranges
    if offset is None:
        offset = size
    elif offset > size:
        raise faults.RangeNotSatisfiable('Supplied offset is beyond object limits')
    if src_object:
        src_account = request.META.get('HTTP_X_SOURCE_ACCOUNT')
        if not src_account:
            src_account = request.user_uniq
        src_container, src_name = split_container_object_string(src_object)
        src_version = request.META.get('HTTP_X_SOURCE_VERSION')
        try:
            src_size, src_hashmap = request.backend.get_object_hashmap(
                request.user_uniq,
                src_account, src_container, src_name, src_version)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Source object does not exist')

        if length is None:
            length = src_size
        elif length > src_size:
            raise faults.BadRequest('Object length is smaller than range length')
    else:
        # Require either a Content-Length, or 'chunked' Transfer-Encoding.
        content_length = -1
        if request.META.get('HTTP_TRANSFER_ENCODING') != 'chunked':
            content_length = get_content_length(request)

        if length is None:
            length = content_length
        else:
            if content_length == -1:
                # TODO: Get up to length bytes in chunks.
                length = content_length
            elif length != content_length:
                raise faults.BadRequest('Content length does not match range length')
    if total is not None and (total != size or offset >= size or (length > 0 and offset + length >= size)):
        raise faults.RangeNotSatisfiable(
            'Supplied range will change provided object limits')

    dest_bytes = request.META.get('HTTP_X_OBJECT_BYTES')
    if dest_bytes is not None:
        dest_bytes = get_int_parameter(dest_bytes)
        if dest_bytes is None:
            raise faults.BadRequest('Invalid X-Object-Bytes header')

    if src_object:
        if offset % request.backend.block_size == 0:
            # Update the hashes only.
            sbi = 0
            while length > 0:
                bi = int(offset / request.backend.block_size)
                bl = min(length, request.backend.block_size)
                if bi < len(hashmap):
                    if bl == request.backend.block_size:
                        hashmap[bi] = src_hashmap[sbi]
                    else:
                        data = request.backend.get_block(src_hashmap[sbi])
                        hashmap[bi] = request.backend.update_block(hashmap[bi],
                                                                   data[:bl], 0)
                else:
                    hashmap.append(src_hashmap[sbi])
                offset += bl
                length -= bl
                sbi += 1
        else:
            data = ''
            sbi = 0
            while length > 0:
                data += request.backend.get_block(src_hashmap[sbi])
                if length < request.backend.block_size:
                    data = data[:length]
                bytes = put_object_block(request, hashmap, data, offset)
                offset += bytes
                data = data[bytes:]
                length -= bytes
                sbi += 1
    else:
        data = ''
        for d in socket_read_iterator(request, length,
                                      request.backend.block_size):
            # TODO: Raise 408 (Request Timeout) if this takes too long.
            # TODO: Raise 499 (Client Disconnect) if a length is defined and we stop before getting this much data.
            data += d
            bytes = put_object_block(request, hashmap, data, offset)
            offset += bytes
            data = data[bytes:]
        if len(data) > 0:
            put_object_block(request, hashmap, data, offset)

    if offset > size:
        size = offset
    if dest_bytes is not None and dest_bytes < size:
        size = dest_bytes
        hashmap = hashmap[:(int((size - 1) / request.backend.block_size) + 1)]
    checksum = hashmap_md5(
        request.backend, hashmap, size) if UPDATE_MD5 else ''
    try:
        version_id = request.backend.update_object_hashmap(request.user_uniq,
                                                           v_account, v_container, v_object, size, prev_meta[
                                                           'type'],
                                                           hashmap, checksum, 'pithos', meta, replace, permissions)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ItemNotExists:
        raise faults.ItemNotFound('Container does not exist')
    except ValueError:
        raise faults.BadRequest('Invalid sharing header')
    except QuotaError, e:
        raise faults.RequestEntityTooLarge('Quota error: %s' % e)
    if public is not None:
        try:
            request.backend.update_object_public(request.user_uniq, v_account,
                                                 v_container, v_object, public)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Object does not exist')

    response = HttpResponse(status=204)
    response['ETag'] = checksum
    response['X-Object-Version'] = version_id
    return response


@api_method('DELETE', user_required=True, logger=logger)
def object_delete(request, v_account, v_container, v_object):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500),
    #                       itemNotFound (404),
    #                       forbidden (403),
    #                       badRequest (400)
    #                       requestentitytoolarge (413)

    until = get_int_parameter(request.GET.get('until'))
    delimiter = request.GET.get('delimiter')

    try:
        request.backend.delete_object(
            request.user_uniq, v_account, v_container,
            v_object, until, delimiter=delimiter)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except ItemNotExists:
        raise faults.ItemNotFound('Object does not exist')
    except QuotaError, e:
        raise faults.RequestEntityTooLarge('Quota error: %s' % e)
    return HttpResponse(status=204)
