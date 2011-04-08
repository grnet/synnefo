#
# Copyright (c) 2010 Greek Research and Technology Network
#

from socket import getfqdn

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from synnefo.api.faults import BadRequest, ResizeNotAllowed, ServiceUnavailable
from synnefo.api.util import random_password
from synnefo.util.rapi import GanetiRapiClient
from synnefo.util.vapclient import request_forwarding as request_vnc_forwarding
from synnefo.logic import backend
from synnefo.logic.utils import get_rsapi_state


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

@server_action('console')
def get_console(request, vm, args):
    """Arrange for an OOB console of the specified type

    This method arranges for an OOB console of the specified type.
    Only "vnc" type consoles are supported for now.
    It uses a running instance of vncauthproxy to setup proper
    VNC forwarding with a random password, then returns the necessary
    VNC connection info to the caller.

    """
    # Normal Response Code: 200
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)
    try:
        console_type = args.get('type', '')
        if console_type != 'VNC':
            raise BadRequest(message="type can only be 'VNC'")
    except KeyError:
        raise BadRequest()

    # Use RAPI to get VNC console information for this instance
    if get_rsapi_state(vm) != 'ACTIVE':
        raise BadRequest(message="Server not in ACTIVE state")
    console_data = rapi.GetInstanceConsole(vm.backend_id)
    if console_data['kind'] != 'vnc':
        raise ServiceUnavailable()

    # Let vncauthproxy decide on the source port.
    # FIXME
    # sport = 0
    sport = console_data['port'] - 1000
    daddr = console_data['host']
    dport = console_data['port']
    passwd = random_password()

    request_vnc_forwarding(sport, daddr, dport, passwd)
    vnc = { 'host': getfqdn(), 'port': sport, 'password': passwd }

    # Format to be reviewed by [verigak], FIXME
    if request.serialization == 'xml':
        mimetype = 'application/xml'
        data = render_to_string('vnc.xml', {'vnc': vnc})
    else:
        mimetype = 'application/json'
        data = json.dumps(vnc)

    return HttpResponse(data, mimetype=mimetype, status=200)


@server_action('changePassword')
def change_password(request, vm, args):
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
def reboot(request, vm, args):
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
def start(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)

    backend.start_action(vm, 'START')
    rapi.StartupInstance(vm.backend_id)
    return HttpResponse(status=202)

@server_action('shutdown')
def shutdown(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)
    
    backend.start_action(vm, 'STOP')
    rapi.ShutdownInstance(vm.backend_id)
    return HttpResponse(status=202)

@server_action('rebuild')
def rebuild(request, vm, args):
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
def resize(request, vm, args):
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
def confirm_resize(request, vm, args):
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
def revert_resize(request, vm, args):
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
