import os
import logging
import hashlib
import types

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json
from django.utils.http import parse_etags

from pithos.api.faults import (Fault, NotModified, BadRequest, Unauthorized, ItemNotFound, Conflict,
    LengthRequired, PreconditionFailed, RangeNotSatisfiable, UnprocessableEntity)
from pithos.api.util import (printable_meta_dict, get_account_meta, put_account_meta,
    get_container_meta, put_container_meta, get_object_meta, put_object_meta,
    validate_modification_preconditions, copy_or_move_object, get_range,
    raw_input_socket, socket_read_iterator, api_method)
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
    elif request.method == 'GET':
        return container_list(request, v_account)
    elif request.method == 'POST':
        return account_update(request, v_account)
    else:
        return method_not_allowed(request)

def container_demux(request, v_account, v_container):
    if request.method == 'HEAD':
        return container_meta(request, v_account, v_container)
    elif request.method == 'GET':
        return object_list(request, v_account, v_container)
    elif request.method == 'PUT':
        return container_create(request, v_account, v_container)
    elif request.method == 'POST':
        return container_update(request, v_account, v_container)
    elif request.method == 'DELETE':
        return container_delete(request, v_account, v_container)
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
    
    meta = backend.get_account_meta(request.user)
    
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
    backend.update_account_meta(request.user, meta)
    return HttpResponse(status=202)

@api_method('GET', format_allowed=True)
def container_list(request, v_account):
    # Normal Response Codes: 200, 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    meta = backend.get_account_meta(request.user)
    
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
        containers = backend.list_containers(request.user, marker, limit)
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
            meta = backend.get_container_meta(request.user, x)
        except NameError:
            continue
        container_meta.append(printable_meta_dict(meta))
    if request.serialization == 'xml':
        data = render_to_string('containers.xml', {'account': request.user, 'containers': container_meta})
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
    
    try:
        meta = backend.get_container_meta(request.user, v_container)
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
        backend.create_container(request.user, v_container)
        ret = 201
    except NameError:
        ret = 202
    
    if len(meta) > 0:
        backend.update_container_meta(request.user, v_container, meta)
    
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
        backend.update_container_meta(request.user, v_container, meta)
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
        backend.delete_container(request.user, v_container)
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
    
    try:
        meta = backend.get_container_meta(request.user, v_container)
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
    
    try:
        objects = backend.list_objects(request.user, v_container, prefix, delimiter, marker, limit, virtual)
    except NameError:
        raise ItemNotFound('Container does not exist')
    
    if request.serialization == 'text':
        if len(objects) == 0:
            # The cloudfiles python bindings expect 200 if json/xml.
            response.status_code = 204
            return response
        response.status_code = 200
        response.content = '\n'.join(objects) + '\n'
        return response
    
    object_meta = []
    for x in objects:
        try:
            meta = backend.get_object_meta(request.user, v_container, x)
        except NameError:
            # Virtual objects/directories.
            if virtual and delimiter and x.endswith(delimiter):
                object_meta.append({"subdir": x})
            continue
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
    
    try:
        meta = backend.get_object_meta(request.user, v_container, v_object)
    except NameError:
        raise ItemNotFound('Object does not exist')
    
    response = HttpResponse(status=204)
    put_object_meta(response, meta)
    return response

@api_method('GET')
def object_read(request, v_account, v_container, v_object):
    # Normal Response Codes: 200, 206
    # Error Response Codes: serviceUnavailable (503),
    #                       rangeNotSatisfiable (416),
    #                       preconditionFailed (412),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       notModified (304)
    
    try:
        meta = backend.get_object_meta(request.user, v_container, v_object)
    except NameError:
        raise ItemNotFound('Object does not exist')
    
    response = HttpResponse()
    put_object_meta(response, meta)
    
    # Range handling.
    range = get_range(request)
    if range is not None:
        offset, length = range
        if offset < 0:
            offset = meta['bytes'] + offset
        if offset > meta['bytes'] or (length and offset + length > meta['bytes']):
            raise RangeNotSatisfiable('Requested range exceeds object limits')
        if not length:
            length = -1
        
        response['Content-Length'] = length # Update with the correct length.
        response.status_code = 206
    else:
        offset = 0
        length = -1
        response.status_code = 200
    
    # Conditions (according to RFC2616 must be evaluated at the end).
    validate_modification_preconditions(request, meta)
    if_match = request.META.get('HTTP_IF_MATCH')
    if if_match is not None and if_match != '*':
        if meta['hash'] not in [x.lower() for x in parse_etags(if_match)]:
            raise PreconditionFailed('Object Etag does not match')    
    if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
    if if_none_match is not None:
        if if_none_match == '*' or meta['hash'] in [x.lower() for x in parse_etags(if_none_match)]:
            raise NotModified('Object Etag matches')
    
    try:
        response.content = backend.get_object(request.user, v_container, v_object, offset, length)
    except NameError:
        raise ItemNotFound('Object does not exist')
    
    return response

@api_method('PUT')
def object_write(request, v_account, v_container, v_object):
    # Normal Response Codes: 201
    # Error Response Codes: serviceUnavailable (503),
    #                       unprocessableEntity (422),
    #                       lengthRequired (411),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    copy_from = request.META.get('HTTP_X_COPY_FROM')
    move_from = request.META.get('HTTP_X_MOVE_FROM')
    if copy_from or move_from:
        # TODO: Why is this required? Copy this ammount?
        content_length = request.META.get('CONTENT_LENGTH')
        if not content_length:
            raise LengthRequired('Missing Content-Length header')
        
        if move_from:
            copy_or_move_object(request, move_from, (v_container, v_object), move=True)
        else:
            copy_or_move_object(request, copy_from, (v_container, v_object), move=False)
        return HttpResponse(status=201)
    
    meta = get_object_meta(request)
    content_length = -1
    if request.META.get('HTTP_TRANSFER_ENCODING') != 'chunked':
        content_length = request.META.get('CONTENT_LENGTH')
        if not content_length:
            raise LengthRequired('Missing Content-Length header')
        try:
            content_length = int(content_length)
            if content_length < 0:
                raise ValueError
        except ValueError:
            raise BadRequest('Invalid Content-Length header')
    # Should be BadRequest, but API says otherwise.
    if 'Content-Type' not in meta:
        raise LengthRequired('Missing Content-Type header')
    
    md5 = hashlib.md5()
    if content_length == 0:
        try:
            backend.update_object(request.user, v_container, v_object, '')
        except NameError:
            raise ItemNotFound('Container does not exist')
    else:
        sock = raw_input_socket(request)
        offset = 0
        for data in socket_read_iterator(sock, content_length):
            # TODO: Raise 408 (Request Timeout) if this takes too long.
            # TODO: Raise 499 (Client Disconnect) if a length is defined and we stop before getting this much data.
            md5.update(data)
            try:
                backend.update_object(request.user, v_container, v_object, data, offset)
            except NameError:
                raise ItemNotFound('Container does not exist')
            offset += len(data)
    
    meta['hash'] = md5.hexdigest().lower()
    etag = request.META.get('HTTP_ETAG')
    if etag and parse_etags(etag)[0].lower() != meta['hash']:
        raise UnprocessableEntity('Object Etag does not match')
    try:
        backend.update_object_meta(request.user, v_container, v_object, meta)
    except NameError:
        raise ItemNotFound('Object does not exist')
    
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
    copy_or_move_object(request, (v_container, v_object), dest_path, move=False)
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
    copy_or_move_object(request, (v_container, v_object), dest_path, move=True)
    return HttpResponse(status=201)

@api_method('POST')
def object_update(request, v_account, v_container, v_object):
    # Normal Response Codes: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    meta = get_object_meta(request)
    if 'Content-Type' in meta:
        del(meta['Content-Type']) # Do not allow changing the Content-Type.
    try:
        backend.update_object_meta(request.user, v_container, v_object, meta)
    except NameError:
        raise ItemNotFound('Object does not exist')
    return HttpResponse(status=202)

@api_method('DELETE')
def object_delete(request, v_account, v_container, v_object):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    try:
        backend.delete_object(request.user, v_container, v_object)
    except NameError:
        raise ItemNotFound('Object does not exist')
    return HttpResponse(status=204)

@api_method()
def method_not_allowed(request):
    raise BadRequest('Method not allowed')
