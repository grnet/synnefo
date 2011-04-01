#
# Copyright (c) 2010 Greek Research and Technology Network
#

from django.conf import settings
from django.http import HttpResponse

from synnefo.api.errors import *
from synnefo.util.rapi import GanetiRapiClient
from synnefo.logic import backend, utils

server_actions = {}

rapi = GanetiRapiClient(*settings.GANETI_CLUSTER_INFO)


def server_action(name):
    def decorator(func):
        server_actions[name] = func
        return func
    return decorator


@server_action('changePassword')
def change_password(server, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)
    
    try:
        adminPass = args['adminPass']
    except KeyError:
        raise BadRequest()

    raise ServiceUnavailable()

@server_action('reboot')
def reboot(server, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)
    
    reboot_type = args.get('type', '')
    if reboot_type not in ('SOFT', 'HARD'):
        raise BadRequest()
    
    backend.start_action(server, 'REBOOT')
    rapi.RebootInstance(server.backend_id, reboot_type.lower())
    return HttpResponse(status=202)

@server_action('start')
def start(server, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503), itemNotFound (404)

    backend.start_action(server, 'START')
    rapi.StartupInstance(server.backend_id)
    return HttpResponse(status=202)

@server_action('shutdown')
def shutdown(server, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503), itemNotFound (404)
    
    backend.start_action(server, 'STOP')
    rapi.ShutdownInstance(server.backend_id)
    return HttpResponse(status=202)

@server_action('rebuild')
def rebuild(server, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       serverCapacityUnavailable (503),
    #                       overLimit (413)

    raise ServiceUnavailable()

@server_action('resize')
def resize(server, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       serverCapacityUnavailable (503),
    #                       overLimit (413),
    #                       resizeNotAllowed (403)
    
    raise ResizeNotAllowed()

@server_action('confirmResize')
def confirm_resize(server, args):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       serverCapacityUnavailable (503),
    #                       overLimit (413),
    #                       resizeNotAllowed (403)
    
    raise ResizeNotAllowed()

@server_action('revertResize')
def revert_resize(server, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       serverCapacityUnavailable (503),
    #                       overLimit (413),
    #                       resizeNotAllowed (403)

    raise ResizeNotAllowed()
