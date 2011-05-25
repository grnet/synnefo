#
# Copyright (c) 2010 Greek Research and Technology Network
#

from socket import getfqdn

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from synnefo.api.faults import BadRequest, ServiceUnavailable
from synnefo.api.util import random_password, get_vm, get_nic
from synnefo.util.vapclient import request_forwarding as request_vnc_forwarding
from synnefo.logic.backend import (reboot_instance, startup_instance, shutdown_instance,
                                    get_instance_console)
from synnefo.logic.utils import get_rsapi_state


server_actions = {}
network_actions = {}


def server_action(name):
    '''Decorator for functions implementing server actions.
    `name` is the key in the dict passed by the client.
    '''

    def decorator(func):
        server_actions[name] = func
        return func
    return decorator

def network_action(name):
    '''Decorator for functions implementing network actions.
    `name` is the key in the dict passed by the client.
    '''

    def decorator(func):
        network_actions[name] = func
        return func
    return decorator


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
        password = args['adminPass']
    except KeyError:
        raise BadRequest('Malformed request.')

    raise ServiceUnavailable('Changing password is not supported.')

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
        raise BadRequest('Malformed Request.')
    reboot_instance(vm, reboot_type.lower())
    return HttpResponse(status=202)

@server_action('start')
def start(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)

    if args:
        raise BadRequest('Malformed Request.')
    startup_instance(vm)
    return HttpResponse(status=202)

@server_action('shutdown')
def shutdown(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)

    if args:
        raise BadRequest('Malformed Request.')
    shutdown_instance(vm)
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

    raise ServiceUnavailable('Rebuild not supported.')

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

    raise ServiceUnavailable('Resize not supported.')

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

    raise ServiceUnavailable('Resize not supported.')

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

    raise ServiceUnavailable('Resize not supported.')

@server_action('console')
def get_console(request, vm, args):
    """Arrange for an OOB console of the specified type

    This method arranges for an OOB console of the specified type.
    Only consoles of type "vnc" are supported for now.

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

    console_type = args.get('type', '')
    if console_type != 'vnc':
        raise BadRequest('Type can only be "vnc".')

    # Use RAPI to get VNC console information for this instance
    if get_rsapi_state(vm) != 'ACTIVE':
        raise BadRequest('Server not in ACTIVE state.')

    if settings.TEST:
        console_data = {'kind': 'vnc', 'host': 'ganeti_node', 'port': 1000}
    else:
        console_data = get_instance_console(vm)

    if console_data['kind'] != 'vnc':
        raise ServiceUnavailable('Could not create a console of requested type.')

    # Let vncauthproxy decide on the source port.
    # The alternative: static allocation, e.g.
    # sport = console_data['port'] - 1000
    sport = 0
    daddr = console_data['host']
    dport = console_data['port']
    password = random_password()

    try:
        if settings.TEST:
            fwd = {'source_port': 1234, 'status': 'OK'}
        else:
            fwd = request_vnc_forwarding(sport, daddr, dport, password)
    except Exception:
        raise ServiceUnavailable('Could not allocate VNC console port.')

    if fwd['status'] != "OK":
        raise ServiceUnavailable('Could not allocate VNC console.')

    console = {
        'type': 'vnc',
        'host': getfqdn(),
        'port': fwd['source_port'],
        'password': password}

    if request.serialization == 'xml':
        mimetype = 'application/xml'
        data = render_to_string('console.xml', {'console': console})
    else:
        mimetype = 'application/json'
        data = json.dumps({'console': console})

    return HttpResponse(data, mimetype=mimetype, status=200)


@network_action('add')
def add(request, net, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       overLimit (413)

    server_id = args.get('serverRef', None)
    if not server_id:
        raise BadRequest('Malformed Request.')
    vm = get_vm(server_id, request.user)
    vm.nics.create(network=net)
    vm.save()
    net.save()
    return HttpResponse(status=202)

@network_action('remove')
def remove(request, net, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       overLimit (413)

    server_id = args.get('serverRef', None)
    if not server_id:
        raise BadRequest('Malformed Request.')
    vm = get_vm(server_id, request.user)
    nic = get_nic(vm, net)
    nic.delete()
    vm.save()
    net.save()
    return HttpResponse(status=202)
