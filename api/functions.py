#
# Copyright (c) 2011 Greek Research and Technology Network
#

from django.http import HttpResponse

from pithos.api.faults import Fault, BadRequest, Unauthorized
from pithos.api.util import api_method

import logging

logging.basicConfig(level=logging.INFO)

@api_method('GET')
def authenticate(request):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400)
    
    logging.debug('request.META: %s' % request.META)
    
    x_auth_user = request.META.get('HTTP_X_AUTH_USER')
    x_auth_key = request.META.get('HTTP_X_AUTH_KEY')
    
    if not x_auth_user or not x_auth_key:
        raise BadRequest('Missing auth user or key.')
    # TODO: Authenticate.
    #if x_auth_user == "test":
    #   raise Unauthorized()
    
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
    # TODO: Check parameter sizes.
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
    return HttpResponse("account_meta: %s" % v_account)

@api_method('GET', format_allowed = True)
def container_list(request, v_account):
    return HttpResponse("container_list: %s" % v_account)

@api_method('HEAD')
def container_meta(request, v_account, v_container):
    return HttpResponse("container_meta: %s %s" % (v_account, v_container))

@api_method('PUT')
def container_create(request, v_account, v_container):
    return HttpResponse("container_create: %s %s" % (v_account, v_container))

@api_method('DELETE')
def container_delete(request, v_account, v_container):
    return HttpResponse("container_delete: %s %s" % (v_account, v_container))

@api_method('GET')
def object_list(request, v_account, v_container):
    return HttpResponse("object_list: %s %s" % (v_account, v_container))

@api_method('HEAD')
def object_meta(request, v_account, v_container, v_object):
    return HttpResponse("object_meta: %s %s %s" % (v_account, v_container, v_object))

@api_method('GET')
def object_read(request, v_account, v_container, v_object):
    return HttpResponse("object_read: %s %s %s" % (v_account, v_container, v_object))

@api_method('PUT')
def object_write(request, v_account, v_container, v_object):
    return HttpResponse("object_write: %s %s %s" % (v_account, v_container, v_object))

@api_method('POST')
def object_update(request, v_account, v_container, v_object):
    return HttpResponse("object_update: %s %s %s" % (v_account, v_container, v_object))

@api_method('DELETE')
def object_delete(request, v_account, v_container, v_object):
    return HttpResponse("object_delete: %s %s %s" % (v_account, v_container, v_object))

@api_method()
def method_not_allowed(request):
    raise BadRequest('Method not allowed.')
