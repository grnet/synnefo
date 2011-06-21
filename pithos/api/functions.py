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

import os
import logging
import hashlib

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json
from django.utils.http import parse_etags

from pithos.api.faults import (Fault, NotModified, BadRequest, Unauthorized, ItemNotFound, Conflict,
    LengthRequired, PreconditionFailed, RangeNotSatisfiable, UnprocessableEntity)
from pithos.api.util import (format_meta_key, printable_meta_dict, get_account_meta,
    put_account_meta, get_container_meta, put_container_meta, get_object_meta, put_object_meta,
    update_manifest_meta, format_permissions, validate_modification_preconditions,
    validate_matching_preconditions, split_container_object_string, copy_or_move_object,
    get_int_parameter, get_content_length, get_content_range, get_sharing, raw_input_socket,
    socket_read_iterator, object_data_response, put_object_block, hashmap_hash, api_method)
from pithos.backends import backend


logger = logging.getLogger(__name__)


def top_demux(request):
    if request.method == 'GET':
        return authenticate(request)
    else:
        return method_not_allowed(request)

def account_demux(request, v_account):
    if request.method == 'HEAD':
        return account_meta(request, v_account)
    elif request.method == 'POST':
        return account_update(request, v_account)
    elif request.method == 'GET':
        return container_list(request, v_account)
    else:
        return method_not_allowed(request)

def container_demux(request, v_account, v_container):
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
        return method_not_allowed(request)

def object_demux(request, v_account, v_container, v_object):
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
        return object_update(request, v_account, v_container, v_object)
    elif request.method == 'DELETE':
        return object_delete(request, v_account, v_container, v_object)
    else:
        return method_not_allowed(request)

@api_method('GET')
def authenticate(request):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    x_auth_user = request.META.get('HTTP_X_AUTH_USER')
    x_auth_key = request.META.get('HTTP_X_AUTH_KEY')
    if not x_auth_user or not x_auth_key:
        raise BadRequest('Missing X-Auth-User or X-Auth-Key header')
    response = HttpResponse(status=204)
    response['X-Auth-Token'] = '0000'
    response['X-Storage-Url'] = os.path.join(request.build_absolute_uri(), 'demo')
    return response

@api_method('HEAD')
def account_meta(request, v_account):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    until = get_int_parameter(request, 'until')
    meta = backend.get_account_meta(request.user, v_account, until)
    
    response = HttpResponse(status=204)
    put_account_meta(response, meta)
    return response

@api_method('POST')
def account_update(request, v_account):
    # Normal Response Codes: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    meta = get_account_meta(request)    
    backend.update_account_meta(request.user, v_account, meta, replace=True)
    return HttpResponse(status=202)

@api_method('GET', format_allowed=True)
def container_list(request, v_account):
    # Normal Response Codes: 200, 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    until = get_int_parameter(request, 'until')
    meta = backend.get_account_meta(request.user, v_account, until)
    
    validate_modification_preconditions(request, meta)
    
    response = HttpResponse()
    put_account_meta(response, meta)
    
    marker = request.GET.get('marker')
    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
            if limit <= 0:
                raise ValueError
        except ValueError:
            limit = 10000
    
    try:
        containers = backend.list_containers(request.user, v_account, marker, limit, until)
    except NameError:
        containers = []
    
    if request.serialization == 'text':
        if len(containers) == 0:
            # The cloudfiles python bindings expect 200 if json/xml.
            response.status_code = 204
            return response
        response.status_code = 200
        response.content = '\n'.join([x[0] for x in containers]) + '\n'
        return response
    
    container_meta = []
    for x in containers:
        if x[1] is not None:
            try:
                meta = backend.get_container_meta(request.user, v_account, x[0], until)
                container_meta.append(printable_meta_dict(meta))
            except NameError:
                pass
    if request.serialization == 'xml':
        data = render_to_string('containers.xml', {'account': v_account, 'containers': container_meta})
    elif request.serialization  == 'json':
        data = json.dumps(container_meta)
    response.status_code = 200
    response.content = data
    return response

@api_method('HEAD')
def container_meta(request, v_account, v_container):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    until = get_int_parameter(request, 'until')
    try:
        meta = backend.get_container_meta(request.user, v_account, v_container, until)
        meta['object_meta'] = backend.list_object_meta(request.user, v_account, v_container, until)
    except NameError:
        raise ItemNotFound('Container does not exist')
    
    response = HttpResponse(status=204)
    put_container_meta(response, meta)
    return response

@api_method('PUT')
def container_create(request, v_account, v_container):
    # Normal Response Codes: 201, 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    meta = get_container_meta(request)
    
    try:
        backend.put_container(request.user, v_account, v_container)
        ret = 201
    except NameError:
        ret = 202
    
    if len(meta) > 0:
        backend.update_container_meta(request.user, v_account, v_container, meta, replace=True)
    
    return HttpResponse(status=ret)

@api_method('POST')
def container_update(request, v_account, v_container):
    # Normal Response Codes: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    meta = get_container_meta(request)
    try:
        backend.update_container_meta(request.user, v_account, v_container, meta, replace=True)
    except NameError:
        raise ItemNotFound('Container does not exist')
    return HttpResponse(status=202)

@api_method('DELETE')
def container_delete(request, v_account, v_container):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       conflict (409),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    try:
        backend.delete_container(request.user, v_account, v_container)
    except NameError:
        raise ItemNotFound('Container does not exist')
    except IndexError:
        raise Conflict('Container is not empty')
    return HttpResponse(status=204)

@api_method('GET', format_allowed=True)
def object_list(request, v_account, v_container):
    # Normal Response Codes: 200, 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    until = get_int_parameter(request, 'until')
    try:
        meta = backend.get_container_meta(request.user, v_account, v_container, until)
        meta['object_meta'] = backend.list_object_meta(request.user, v_account, v_container, until)
    except NameError:
        raise ItemNotFound('Container does not exist')
    
    validate_modification_preconditions(request, meta)
    
    response = HttpResponse()
    put_container_meta(response, meta)
    
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
    if prefix and delimiter:
        prefix = prefix + delimiter
    if not prefix:
        prefix = ''
    prefix = prefix.lstrip('/')
    
    marker = request.GET.get('marker')
    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
            if limit <= 0:
                raise ValueError
        except ValueError:
            limit = 10000
    
    keys = request.GET.get('meta')
    if keys:
        keys = keys.split(',')
        keys = [format_meta_key('X-Object-Meta-' + x.strip()) for x in keys if x.strip() != '']
    else:
        keys = []
    
    try:
        objects = backend.list_objects(request.user, v_account, v_container, prefix, delimiter, marker, limit, virtual, keys, until)
    except NameError:
        raise ItemNotFound('Container does not exist')
    
    if request.serialization == 'text':
        if len(objects) == 0:
            # The cloudfiles python bindings expect 200 if json/xml.
            response.status_code = 204
            return response
        response.status_code = 200
        response.content = '\n'.join([x[0] for x in objects]) + '\n'
        return response
    
    object_meta = []
    for x in objects:
        if x[1] is None:
            # Virtual objects/directories.
            object_meta.append({'subdir': x[0]})
        else:
            try:
                meta = backend.get_object_meta(request.user, v_account, v_container, x[0], x[1])
                permissions = backend.get_object_permissions(request.user, v_account, v_container, x[0])
            except NameError:
                pass
            if permissions:
                meta['X-Object-Sharing'] = format_permissions(permissions)
            object_meta.append(printable_meta_dict(meta))
    if request.serialization == 'xml':
        data = render_to_string('objects.xml', {'container': v_container, 'objects': object_meta})
    elif request.serialization  == 'json':
        data = json.dumps(object_meta)
    response.status_code = 200
    response.content = data
    return response

@api_method('HEAD')
def object_meta(request, v_account, v_container, v_object):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    version = get_int_parameter(request, 'version')
    try:
        meta = backend.get_object_meta(request.user, v_account, v_container, v_object, version)
        permissions = backend.get_object_permissions(request.user, v_account, v_container, v_object)
    except NameError:
        raise ItemNotFound('Object does not exist')
    except IndexError:
        raise ItemNotFound('Version does not exist')
    
    if permissions:
        meta['X-Object-Sharing'] = format_permissions(permissions)
    update_manifest_meta(request, v_account, meta)
    
    response = HttpResponse(status=200)
    put_object_meta(response, meta)
    return response

@api_method('GET', format_allowed=True)
def object_read(request, v_account, v_container, v_object):
    # Normal Response Codes: 200, 206
    # Error Response Codes: serviceUnavailable (503),
    #                       rangeNotSatisfiable (416),
    #                       preconditionFailed (412),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       notModified (304)
    
    version = get_int_parameter(request, 'version')
    version_list = False
    if version is None and request.GET.get('version') == 'list':
        version_list = True
    try:
        meta = backend.get_object_meta(request.user, v_account, v_container, v_object, version)
        permissions = backend.get_object_permissions(request.user, v_account, v_container, v_object)
    except NameError:
        raise ItemNotFound('Object does not exist')
    except IndexError:
        raise ItemNotFound('Version does not exist')
    
    if permissions:
        meta['X-Object-Sharing'] = format_permissions(permissions)
    update_manifest_meta(request, v_account, meta)
    
    # Evaluate conditions.
    validate_modification_preconditions(request, meta)
    try:
        validate_matching_preconditions(request, meta)
    except NotModified:
        response = HttpResponse(status=304)
        response['ETag'] = meta['hash']
        return response
    
    # Reply with the version list.
    if version_list:
        if request.serialization == 'text':
            raise BadRequest('No format specified for version list.')
        
        d = {'versions': backend.list_versions(request.user, v_account, v_container, v_object)}
        if request.serialization == 'xml':
            d['object'] = v_object
            data = render_to_string('versions.xml', d)
        elif request.serialization  == 'json':
            data = json.dumps(d)
        
        response = HttpResponse(data, status=200)
        put_object_meta(response, meta)
        response['Content-Length'] = len(data)
        return response
    
    sizes = []
    hashmaps = []
    if 'X-Object-Manifest' in meta:
        try:
            src_container, src_name = split_container_object_string('/' + meta['X-Object-Manifest'])
            objects = backend.list_objects(request.user, v_account, src_container, prefix=src_name, virtual=False)
        except ValueError:
            raise BadRequest('Invalid X-Object-Manifest header')
        except NameError:
            raise ItemNotFound('Container does not exist')
        
        try:
            for x in objects:
                s, h = backend.get_object_hashmap(request.user, v_account, src_container, x[0], x[1])
                sizes.append(s)
                hashmaps.append(h)
        except NameError:
            raise ItemNotFound('Object does not exist')
        except IndexError:
            raise ItemNotFound('Version does not exist')
    else:
        try:
            s, h = backend.get_object_hashmap(request.user, v_account, v_container, v_object, version)
            sizes.append(s)
            hashmaps.append(h)
        except NameError:
            raise ItemNotFound('Object does not exist')
        except IndexError:
            raise ItemNotFound('Version does not exist')
    
    # Reply with the hashmap.
    if request.serialization != 'text':
        size = sum(sizes)
        hashmap = sum(hashmaps, [])
        d = {'block_size': backend.block_size, 'block_hash': backend.hash_algorithm, 'bytes': size, 'hashes': hashmap}
        if request.serialization == 'xml':
            d['object'] = v_object
            data = render_to_string('hashes.xml', d)
        elif request.serialization  == 'json':
            data = json.dumps(d)
        
        response = HttpResponse(data, status=200)
        put_object_meta(response, meta)
        response['Content-Length'] = len(data)
        return response
    
    return object_data_response(request, sizes, hashmaps, meta)

@api_method('PUT')
def object_write(request, v_account, v_container, v_object):
    # Normal Response Codes: 201
    # Error Response Codes: serviceUnavailable (503),
    #                       unprocessableEntity (422),
    #                       lengthRequired (411),
    #                       conflict (409),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    copy_from = request.META.get('HTTP_X_COPY_FROM')
    move_from = request.META.get('HTTP_X_MOVE_FROM')
    if copy_from or move_from:
        # TODO: Why is this required? Copy this ammount?
        content_length = get_content_length(request)
        
        if move_from:
            try:
                src_container, src_name = split_container_object_string(move_from)
            except ValueError:
                raise BadRequest('Invalid X-Move-From header')
            copy_or_move_object(request, v_account, src_container, src_name, v_container, v_object, move=True)
        else:
            try:
                src_container, src_name = split_container_object_string(copy_from)
            except ValueError:
                raise BadRequest('Invalid X-Copy-From header')
            copy_or_move_object(request, v_account, src_container, src_name, v_container, v_object, move=False)
        return HttpResponse(status=201)
    
    meta = get_object_meta(request)
    permissions = get_sharing(request)
    content_length = -1
    if request.META.get('HTTP_TRANSFER_ENCODING') != 'chunked':
        content_length = get_content_length(request)
    # Should be BadRequest, but API says otherwise.
    if 'Content-Type' not in meta:
        raise LengthRequired('Missing Content-Type header')
    
    md5 = hashlib.md5()
    size = 0
    hashmap = []
    sock = raw_input_socket(request)
    for data in socket_read_iterator(sock, content_length, backend.block_size):
        # TODO: Raise 408 (Request Timeout) if this takes too long.
        # TODO: Raise 499 (Client Disconnect) if a length is defined and we stop before getting this much data.
        size += len(data)
        hashmap.append(backend.put_block(data))
        md5.update(data)
    
    meta['hash'] = md5.hexdigest().lower()
    etag = request.META.get('HTTP_ETAG')
    if etag and parse_etags(etag)[0].lower() != meta['hash']:
        raise UnprocessableEntity('Object ETag does not match')
    
    try:
        backend.update_object_hashmap(request.user, v_account, v_container, v_object, size, hashmap, meta, True, permissions)
    except NameError:
        raise ItemNotFound('Container does not exist')
    except ValueError:
        raise BadRequest('Invalid sharing header')
    except AttributeError:
        raise Conflict('Sharing already set above or below this path in the hierarchy')
    
    response = HttpResponse(status=201)
    response['ETag'] = meta['hash']
    return response

@api_method('COPY')
def object_copy(request, v_account, v_container, v_object):
    # Normal Response Codes: 201
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    dest_path = request.META.get('HTTP_DESTINATION')
    if not dest_path:
        raise BadRequest('Missing Destination header')
    try:
        dest_container, dest_name = split_container_object_string(dest_path)
    except ValueError:
        raise BadRequest('Invalid Destination header')
    copy_or_move_object(request, v_account, v_container, v_object, dest_container, dest_name, move=False)
    return HttpResponse(status=201)

@api_method('MOVE')
def object_move(request, v_account, v_container, v_object):
    # Normal Response Codes: 201
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    dest_path = request.META.get('HTTP_DESTINATION')
    if not dest_path:
        raise BadRequest('Missing Destination header')
    try:
        dest_container, dest_name = split_container_object_string(dest_path)
    except ValueError:
        raise BadRequest('Invalid Destination header')
    copy_or_move_object(request, v_account, v_container, v_object, dest_container, dest_name, move=True)
    return HttpResponse(status=201)

@api_method('POST')
def object_update(request, v_account, v_container, v_object):
    # Normal Response Codes: 202, 204
    # Error Response Codes: serviceUnavailable (503),
    #                       conflict (409),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    meta = get_object_meta(request)
    permissions = get_sharing(request)
    content_type = meta.get('Content-Type')
    if content_type:
        del(meta['Content-Type']) # Do not allow changing the Content-Type.
    
    try:
        prev_meta = backend.get_object_meta(request.user, v_account, v_container, v_object)
    except NameError:
        raise ItemNotFound('Object does not exist')
    
    # Handle metadata changes.
    if len(meta) != 0:
        # Keep previous values of 'Content-Type' and 'hash'.
        for k in ('Content-Type', 'hash'):
            if k in prev_meta:
                meta[k] = prev_meta[k]
        try:
            backend.update_object_meta(request.user, v_account, v_container, v_object, meta, replace=True)
        except NameError:
            raise ItemNotFound('Object does not exist')
    
    # Handle permission changes.
    if permissions:
        try:
            backend.update_object_permissions(request.user, v_account, v_container, v_object, permissions)
        except NameError:
            raise ItemNotFound('Object does not exist')
        except ValueError:
            raise BadRequest('Invalid sharing header')
        except AttributeError:
            raise Conflict('Sharing already set above or below this path in the hierarchy')
    
    # TODO: Merge above functions with updating the hashmap if there is data in the request.
    
    # A Content-Type or Content-Range header may indicate data updates.
    if content_type is None:
        return HttpResponse(status=202)
    if content_type.startswith('multipart/byteranges'):
        # TODO: Support multiple update ranges.
        return HttpResponse(status=202)
    # Single range update. Range must be in Content-Range.
    # Based on: http://code.google.com/p/gears/wiki/ContentRangePostProposal
    # (with the addition that '*' is allowed for the range - will append).
    if content_type != 'application/octet-stream':
        return HttpResponse(status=202)
    content_range = request.META.get('HTTP_CONTENT_RANGE')
    if not content_range:
        return HttpResponse(status=202)
    ranges = get_content_range(request)
    if not ranges:
        return HttpResponse(status=202)
    # Require either a Content-Length, or 'chunked' Transfer-Encoding.
    content_length = -1
    if request.META.get('HTTP_TRANSFER_ENCODING') != 'chunked':
        content_length = get_content_length(request)
    
    try:
        size, hashmap = backend.get_object_hashmap(request.user, v_account, v_container, v_object)
    except NameError:
        raise ItemNotFound('Object does not exist')
    
    offset, length, total = ranges
    if offset is None:
        offset = size
    elif offset > size:
        raise RangeNotSatisfiable('Supplied offset is beyond object limits')
    if length is None or content_length == -1:
        length = content_length # Nevermind the error.
    elif length != content_length:
        raise BadRequest('Content length does not match range length')
    if total is not None and (total != size or offset >= size or (length > 0 and offset + length >= size)):
        raise RangeNotSatisfiable('Supplied range will change provided object limits')
    
    sock = raw_input_socket(request)
    data = ''
    for d in socket_read_iterator(sock, length, backend.block_size):
        # TODO: Raise 408 (Request Timeout) if this takes too long.
        # TODO: Raise 499 (Client Disconnect) if a length is defined and we stop before getting this much data.
        data += d
        bytes = put_object_block(hashmap, data, offset)
        offset += bytes
        data = data[bytes:]
    if len(data) > 0:
        put_object_block(hashmap, data, offset)
    
    if offset > size:
        size = offset
    meta = {'hash': hashmap_hash(hashmap)} # Update ETag.
    try:
        backend.update_object_hashmap(request.user, v_account, v_container, v_object, size, hashmap, meta, False)
    except NameError:
        raise ItemNotFound('Container does not exist')
    except ValueError:
        raise BadRequest('Invalid sharing header')
    except AttributeError:
        raise Conflict('Sharing already set above or below this path in the hierarchy')
    
    response = HttpResponse(status=204)
    response['ETag'] = meta['hash']
    return response

@api_method('DELETE')
def object_delete(request, v_account, v_container, v_object):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    try:
        backend.delete_object(request.user, v_account, v_container, v_object)
    except NameError:
        raise ItemNotFound('Object does not exist')
    return HttpResponse(status=204)

@api_method()
def method_not_allowed(request):
    raise BadRequest('Method not allowed')
