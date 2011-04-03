#
# Copyright (c) 2010 Greek Research and Technology Network
#

from django.conf import settings
from django.http import HttpResponse

from synnefo.api.faults import BadRequest, ResizeNotAllowed, ServiceUnavailable
from synnefo.util.rapi import GanetiRapiClient
from synnefo.logic import backend


server_actions = {}

rapi = GanetiRapiClient(*settings.GANETI_CLUSTER_INFO)


def server_action(name):
    '''Decorator for functions implementing server actions.
    
       `name` is the key in the dict passed by the client.
    '''
    
    def decorator(func):
        server_actions[name] = func
        return func
    return decorator


@server_action('changePassword')
def change_password(vm, args):
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
def reboot(vm, args):
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
    
    backend.start_action(vm, 'REBOOT')
    rapi.RebootInstance(vm.backend_id, reboot_type.lower())
    return HttpResponse(status=202)

@server_action('start')
def start(vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)

    backend.start_action(vm, 'START')
    rapi.StartupInstance(vm.backend_id)
    return HttpResponse(status=202)

@server_action('shutdown')
def shutdown(vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)
    
    backend.start_action(vm, 'STOP')
    rapi.ShutdownInstance(vm.backend_id)
    return HttpResponse(status=202)

@server_action('rebuild')
def rebuild(vm, args):
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
def resize(vm, args):
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
def confirm_resize(vm, args):
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
def revert_resize(vm, args):
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
