#
# Copyright (c) 2011 Greek Research and Technology Network
#

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from pithos.api.faults import Fault, BadRequest, Unauthorized
from pithos.api.util import api_method

from pithos.backends.dummy_debug import *

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
    # TODO: Do we support redirections?
    #response['X-Storage-Url'] = 'https://storage.grnet.gr/pithos/v1.0/<some reference>'
    return response

def account_demux(request, v_account):
    if request.method == 'HEAD':
        return account_meta(request, v_account)
    elif request.method == 'GET':
        return container_list(request, v_account)
    else:
        return method_not_allowed(request)

def container_demux(request, v_account, v_container):
    if request.method == 'HEAD':
        return container_meta(request, v_account, v_container)
    elif request.method == 'GET':
        return object_list(request, v_account, v_container)
    elif request.method == 'PUT':
        return container_create(request, v_account, v_container)
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
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    container_count, bytes_count = get_account_meta(request.user)
    
    response = HttpResponse(status = 204)
    response['X-Account-Container-Count'] = container_count
    response['X-Account-Total-Bytes-Used'] = bytes_count
    return response

@api_method('GET', format_allowed = True)
def container_list(request, v_account):
    # Normal Response Codes: 200, 204
    # Error Response Codes: serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    marker = request.GET.get('marker')
    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            limit = None
    
    containers = list_containers(request.user, marker, limit)
    if len(containers) == 0:
        return HttpResponse(status = 204)
    
    if request.serialization == 'xml':
        data = render_to_string('containers.xml', {'account': request.user, 'containers': containers})
    elif request.serialization  == 'json':
        data = json.dumps(containers)
    else:
        data = '\n'.join(x['name'] for x in containers)
    
    return HttpResponse(data, status = 200)

@api_method('HEAD')
def container_meta(request, v_account, v_container):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    object_count, bytes_count = get_container_meta(request.user, v_container)
    
    response = HttpResponse(status = 204)
    response['X-Container-Object-Count'] = object_count
    response['X-Container-Bytes-Used'] = bytes_count
    return response

@api_method('PUT')
def container_create(request, v_account, v_container):
    # Normal Response Codes: 201, 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)

    if create_container(request.user, v_container):
        return HttpResponse(status = 201)
    else:
        return HttpResponse(status = 202)

@api_method('DELETE')
def container_delete(request, v_account, v_container):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    object_count, bytes_count = get_container_meta(request.user, v_container)
    if object_count > 0:
        return HttpResponse(status = 409)
    
    delete_container(request.user, v_container)
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
    logging.debug("path: %s", path)
    
    # Path overrides prefix and delimiter.
    if path:
        prefix = path
        delimiter = '/'
    # Naming policy.
    if prefix and delimiter:
        prefix = prefix + delimiter
    
    marker = request.GET.get('marker')
    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            limit = None
    
    objects = list_objects(request.user, v_container, prefix, delimiter, marker, limit)
    if len(objects) == 0:
        return HttpResponse(status = 204)
    
    if request.serialization == 'xml':
        data = render_to_string('objects.xml', {'container': v_container, 'objects': objects})
    elif request.serialization  == 'json':
        data = json.dumps(objects)
    else:
        data = '\n'.join(x['name'] for x in objects)
    
    return HttpResponse(data, status = 200)

@api_method('HEAD')
def object_meta(request, v_account, v_container, v_object):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)

    info = get_object_meta(request.user, v_container, v_object)
    
    response = HttpResponse(status = 204)
    response['ETag'] = info['hash']
    response['Content-Length'] = info['bytes']
    response['Content-Type'] = info['content_type']
    # TODO: Format time.
    response['Last-Modified'] = info['last_modified']
    for k, v in info['meta'].iteritems():
        response['X-Object-Meta-%s' % k.capitalize()] = v
    
    return response

@api_method('GET')
def object_read(request, v_account, v_container, v_object):
    return HttpResponse("object_read: %s %s %s" % (v_account, v_container, v_object))

@api_method('PUT')
def object_write(request, v_account, v_container, v_object):
    return HttpResponse("object_write: %s %s %s" % (v_account, v_container, v_object))

@api_method('POST')
def object_update(request, v_account, v_container, v_object):
    # Normal Response Codes: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    prefix = 'X-Object-Meta-'
    meta = dict([(k[len(prefix):].lower(), v) for k, v in request.POST.iteritems() if k.startswith(prefix)])
    
    update_object_meta(request.user, v_container, v_object, meta)
    return HttpResponse(status = 202)

@api_method('DELETE')
def object_delete(request, v_account, v_container, v_object):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    delete_object(request.user, v_container, v_object)
    return HttpResponse(status = 204)

@api_method()
def method_not_allowed(request):
    raise BadRequest('Method not allowed.')
