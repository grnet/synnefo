#
# Copyright (c) 2011 Greek Research and Technology Network
#

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json
from django.utils.http import http_date, parse_etags

try:
    from django.utils.http import parse_http_date_safe
except:
    from pithos.api.util import parse_http_date_safe

from pithos.api.faults import Fault, NotModified, BadRequest, Unauthorized, ItemNotFound, LengthRequired, PreconditionFailed, RangeNotSatisfiable, UnprocessableEntity
from pithos.api.util import get_meta, get_range, api_method

from settings import PROJECT_PATH
from os import path
STORAGE_PATH = path.join(PROJECT_PATH, 'data')

from pithos.backends.dummy import BackEnd

import logging

logging.basicConfig(level=logging.DEBUG)

@api_method('GET')
def authenticate(request):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    x_auth_user = request.META.get('HTTP_X_AUTH_USER')
    x_auth_key = request.META.get('HTTP_X_AUTH_KEY')
    
    if not x_auth_user or not x_auth_key:
        raise BadRequest('Missing auth user or key.')
    
    response = HttpResponse(status = 204)
    response['X-Auth-Token'] = 'eaaafd18-0fed-4b3a-81b4-663c99ec1cbb'
    # TODO: Must support X-Storage-Url to be compatible.
    response['X-Storage-Url'] = 'http://127.0.0.1:8000/v1/asdf'
    return response

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
    elif request.method == 'POST':
        return object_update(request, v_account, v_container, v_object)
    elif request.method == 'DELETE':
        return object_delete(request, v_account, v_container, v_object)
    else:
        return method_not_allowed(request)

@api_method('HEAD')
def account_meta(request, v_account):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    be = BackEnd(STORAGE_PATH)
    try:
        info = be.get_account_meta(request.user)
    except NameError:
        info = {'count': 0, 'bytes': 0}
    
    response = HttpResponse(status = 204)
    response['X-Account-Container-Count'] = info['count']
    response['X-Account-Bytes-Used'] = info['bytes']
    for k in [x for x in info.keys() if x.startswith('X-Account-Meta-')]:
        response[k] = info[k]
    
    return response

@api_method('POST')
def account_update(request, v_account):
    # Normal Response Codes: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    meta = get_meta(request, 'X-Account-Meta-')
    
    be = BackEnd(STORAGE_PATH)
    be.update_account_meta(request.user, meta)
    
    return HttpResponse(status = 202)

@api_method('GET', format_allowed = True)
def container_list(request, v_account):
    # Normal Response Codes: 200, 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    marker = request.GET.get('marker')
    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            limit = 10000
    
    be = BackEnd(STORAGE_PATH)
    try:
        containers = be.list_containers(request.user, marker, limit)
    except NameError:
        containers = []
    # TODO: The cloudfiles python bindings expect 200 if json/xml.
    if len(containers) == 0:
        return HttpResponse(status = 204)
    
    if request.serialization == 'text':
        return HttpResponse('\n'.join(containers), status = 200)
    
    # TODO: Do this with a backend parameter?
    try:
        containers = [be.get_container_meta(request.user, x) for x in containers]
    except NameError:
        raise ItemNotFound()
    # TODO: Format dates.
    if request.serialization == 'xml':
        data = render_to_string('containers.xml', {'account': request.user, 'containers': containers})
    elif request.serialization  == 'json':
        data = json.dumps(containers)
    return HttpResponse(data, status = 200)

@api_method('HEAD')
def container_meta(request, v_account, v_container):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    be = BackEnd(STORAGE_PATH)
    try:
        info = be.get_container_meta(request.user, v_container)
    except NameError:
        raise ItemNotFound()
    
    response = HttpResponse(status = 204)
    response['X-Container-Object-Count'] = info['count']
    response['X-Container-Bytes-Used'] = info['bytes']
    for k in [x for x in info.keys() if x.startswith('X-Container-Meta-')]:
        response[k] = info[k]
    
    return response

@api_method('PUT')
def container_create(request, v_account, v_container):
    # Normal Response Codes: 201, 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    meta = get_meta(request, 'X-Container-Meta-')
    
    be = BackEnd(STORAGE_PATH)
    try:
        be.create_container(request.user, v_container)
        ret = 201
    except NameError:
        ret = 202
    
    if len(meta) > 0:
        be.update_container_meta(request.user, v_container, meta)
    
    return HttpResponse(status = ret)

@api_method('POST')
def container_update(request, v_account, v_container):
    # Normal Response Codes: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    meta = get_meta(request, 'X-Container-Meta-')
    
    be = BackEnd(STORAGE_PATH)
    try:
        be.update_container_meta(request.user, v_container, meta)
    except NameError:
        raise ItemNotFound()
    
    return HttpResponse(status = 202)

@api_method('DELETE')
def container_delete(request, v_account, v_container):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    be = BackEnd(STORAGE_PATH)
    try:
        info = be.get_container_meta(request.user, v_container)
    except NameError:
        raise ItemNotFound()
    
    if info['count'] > 0:
        return HttpResponse(status = 409)
    
    # TODO: Handle both exceptions.
    try:
        be.delete_container(request.user, v_container)
    except:
        raise ItemNotFound()
    return HttpResponse(status = 204)

@api_method('GET', format_allowed = True)
def object_list(request, v_account, v_container):
    # Normal Response Codes: 200, 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    path = request.GET.get('path')
    prefix = request.GET.get('prefix')
    delimiter = request.GET.get('delimiter')
    
    # Path overrides prefix and delimiter.
    if path:
        prefix = path
        delimiter = '/'
    # Naming policy.
    if prefix and delimiter:
        prefix = prefix + delimiter
    if not prefix:
        prefix = ''
    
    marker = request.GET.get('marker')
    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            limit = 10000
    
    be = BackEnd(STORAGE_PATH)
    try:
        objects = be.list_objects(request.user, v_container, prefix, delimiter, marker, limit)
    except NameError:
        raise ItemNotFound()
    # TODO: The cloudfiles python bindings expect 200 if json/xml.
    if len(objects) == 0:
        return HttpResponse(status = 204)
    
    if request.serialization == 'text':
        return HttpResponse('\n'.join(objects), status = 200)
    
    # TODO: Do this with a backend parameter?
    try:
        objects = [be.get_object_meta(request.user, v_container, x) for x in objects]
    except NameError:
        raise ItemNotFound()
    # TODO: Format dates.
    if request.serialization == 'xml':
        data = render_to_string('objects.xml', {'container': v_container, 'objects': objects})
    elif request.serialization  == 'json':
        data = json.dumps(objects)
    return HttpResponse(data, status = 200)

@api_method('HEAD')
def object_meta(request, v_account, v_container, v_object):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    be = BackEnd(STORAGE_PATH)
    try:
        info = be.get_object_meta(request.user, v_container, v_object)
    except NameError:
        raise ItemNotFound()
    
    response = HttpResponse(status = 204)
    response['ETag'] = info['hash']
    response['Content-Length'] = info['bytes']
    response['Content-Type'] = info['content_type']
    response['Last-Modified'] = http_date(info['last_modified'])
    for k in [x for x in info.keys() if x.startswith('X-Object-Meta-')]:
        response[k] = info[k]
    
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
    
    be = BackEnd(STORAGE_PATH)
    try:
        info = be.get_object_meta(request.user, v_container, v_object)
    except NameError:
        raise ItemNotFound()
    
    # TODO: Check if the cloudfiles python bindings expect hash/content_type/last_modified on range requests.
    response = HttpResponse()
    response['ETag'] = info['hash']
    response['Content-Type'] = info['content_type']
    response['Last-Modified'] = http_date(info['last_modified'])
    
    # Range handling.
    range = get_range(request)
    if range is not None:
        offset, length = range
        if length:
            if offset + length > info['bytes']:
                raise RangeNotSatisfiable()
        else:
            if offset > info['bytes']:
                raise RangeNotSatisfiable()
        if not length:
            length = -1
        
        response['Content-Length'] = length        
        response.status_code = 206
    else:
        offset = 0
        length = -1
        
        response['Content-Length'] = info['bytes']
        response.status_code = 200
    
    # Conditions (according to RFC2616 must be evaluated at the end).
    # TODO: Check etag/date conditions.
    if_match = request.META.get('HTTP_IF_MATCH')
    if if_match is not None and if_match != '*':
        if info['hash'] not in parse_etags(if_match):
            raise PreconditionFailed()
    
    if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
    if if_none_match is not None:
        if if_none_match == '*' or info['hash'] in parse_etags(if_none_match):
            raise NotModified()
    
    if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')
    if if_modified_since is not None:
        if_modified_since = parse_http_date_safe(if_modified_since)
    if if_modified_since is not None and info['last_modified'] <= if_modified_since:
        raise NotModified()

    if_unmodified_since = request.META.get('HTTP_IF_UNMODIFIED_SINCE')
    if if_unmodified_since is not None:
        if_unmodified_since = parse_http_date_safe(if_unmodified_since)
    if if_unmodified_since is not None and info['last_modified'] > if_unmodified_since:
        raise PreconditionFailed()
    
    try:
        response.content = be.get_object(request.user, v_container, v_object, offset, length)
    except NameError:
        raise ItemNotFound()
    
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
    
    be = BackEnd(STORAGE_PATH)
    
    copy_from = request.META.get('HTTP_X_COPY_FROM')
    if copy_from:
        parts = copy_from.split('/')
        if len(parts) < 3 or parts[0] != '':
            raise BadRequest('Bad X-Copy-From path.')
        copy_container = parts[1]
        copy_name = '/'.join(parts[2:])
        
        try:
            info = be.get_object_meta(request.user, copy_container, copy_name)
        except NameError:
            raise ItemNotFound()
        
        content_length = request.META.get('CONTENT_LENGTH')
        content_type = request.META.get('CONTENT_TYPE')
        # TODO: Why is this required? Copy this ammount?
        if not content_length:
            raise LengthRequired()
        if content_type:
            info['content_type'] = content_type
        
        meta = get_meta(request, 'X-Object-Meta-')
        info.update(meta)
        
        try:
            be.copy_object(request.user, copy_container, copy_name, v_container, v_object)
            be.update_object_meta(request.user, v_container, v_object, info)
        except NameError:
            raise ItemNotFound()
        
        response = HttpResponse(status = 201)
    else:
        content_length = request.META.get('CONTENT_LENGTH')
        content_type = request.META.get('CONTENT_TYPE')
        if not content_length or not content_type:
            raise LengthRequired()
        
        info = {'content_type': content_type}
        meta = get_meta(request, 'X-Object-Meta-')
        info.update(meta)
        
        data = request.raw_post_data
        try:
            be.update_object(request.user, v_container, v_object, data)
            be.update_object_meta(request.user, v_container, v_object, info)
        except NameError:
            raise ItemNotFound()
        
        # TODO: Check before update?
        info = be.get_object_meta(request.user, v_container, v_object)
        etag = request.META.get('HTTP_ETAG')
        if etag:
            etag = parse_etags(etag)[0] # TODO: Unescape properly.
            if etag != info['hash']:
                be.delete_object(request.user, v_container, v_object)
                raise UnprocessableEntity()
        
        response = HttpResponse(status = 201)
        response['ETag'] = info['hash']
    
    return response

@api_method('COPY')
def object_copy(request, v_account, v_container, v_object):
    # Normal Response Codes: 201
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    destination = request.META.get('HTTP_DESTINATION')
    if not destination:
        raise BadRequest('Missing Destination.');
    
    parts = destination.split('/')
    if len(parts) < 3 or parts[0] != '':
        raise BadRequest('Bad Destination path.')
    dest_container = parts[1]
    dest_name = '/'.join(parts[2:])
    
    be = BackEnd(STORAGE_PATH)
    try:
        info = be.get_object_meta(request.user, v_container, v_object)
    except NameError:
        raise ItemNotFound()
    
    content_type = request.META.get('CONTENT_TYPE')
    if content_type:
        info['content_type'] = content_type
    meta = get_meta(request, 'X-Object-Meta-')
    info.update(meta)
    
    try:
        be.copy_object(request.user, v_container, v_object, dest_container, dest_name)
        be.update_object_meta(request.user, dest_container, dest_name, info)
    except NameError:
        raise ItemNotFound()
    
    response = HttpResponse(status = 201)

@api_method('POST')
def object_update(request, v_account, v_container, v_object):
    # Normal Response Codes: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    return HttpResponse(status = 202)

@api_method('DELETE')
def object_delete(request, v_account, v_container, v_object):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    be = BackEnd(STORAGE_PATH)
    try:
        be.delete_object(request.user, v_container, v_object)
    except NameError:
        raise ItemNotFound()
    return HttpResponse(status = 204)

@api_method()
def method_not_allowed(request):
    raise BadRequest('Method not allowed.')
