# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
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

from socket import getfqdn
from vncauthproxy.client import request_forwarding as request_vnc_forwarding

from django.db import transaction
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from snf_django.lib.api import faults
from synnefo.api import util
from synnefo.api.util import (random_password, get_vm, get_nic_from_index,
                              get_network_free_address)
from synnefo.db.models import NetworkInterface
from synnefo.db.pools import EmptyPool
from synnefo.logic import backend
from synnefo.logic.utils import get_rsapi_state

from logging import getLogger
log = getLogger(__name__)


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

    raise faults.NotImplemented('Changing password is not supported.')


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

    log.info("Reboot VM %s", vm)
    reboot_type = args.get('type', '')
    if reboot_type not in ('SOFT', 'HARD'):
        raise faults.BadRequest('Malformed Request.')
    backend.reboot_instance(vm, reboot_type.lower())
    return HttpResponse(status=202)


@server_action('start')
def start(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)

    log.info("Start VM %s", vm)
    if args:
        raise faults.BadRequest('Malformed Request.')
    backend.startup_instance(vm)
    return HttpResponse(status=202)


@server_action('shutdown')
def shutdown(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)

    log.info("Shutdown VM %s", vm)
    if args:
        raise faults.BadRequest('Malformed Request.')
    backend.shutdown_instance(vm)
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

    raise faults.NotImplemented('Rebuild not supported.')


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
    log.debug("resize %s: %s", vm, args)
    flavorRef = args.get("flavorRef", None)
    if flavorRef is None:
        raise faults.BadRequest("Missing 'flavorRef' attribute")

    new_flavor = util.get_flavor(flavor_id=flavorRef, include_deleted=False)
    old_flavor = vm.flavor
    # User requested the same flavor
    if old_flavor.id == new_flavor.id:
        return HttpResponse(status=200)
    # Check that resize can be performed
    if old_flavor.disk != new_flavor.disk:
        raise faults.BadRequest("Can not resize instance disk")
    if old_flavor.disk_template != new_flavor.disk_template:
        raise faults.BadRequest("Can not change instance disk template")

    if not vm_is_stopped(vm):
        raise faults.BadRequest("Can not resize running instance")

    vcpus, memory = new_flavor.cpu, new_flavor.ram
    jobId = backend.resize_instance(vm, vcpus=vcpus, memory=memory)

    log.info("User '%s' resized VM from flavor '%s' to '%s', job %s",
              request.user_uniq, old_flavor, new_flavor, jobId)

    # Save operstate now, since you don't want any other action when an
    # an instance is resizing
    vm.operstate = "RESIZE"
    util.start_action(vm, "RESIZE", jobId)

    vm.save()
    return HttpResponse(status=202)


def vm_is_stopped(vm):
    """Check if a VirtualMachine is currently stopped.

    A server is stopped if it's operstate is 'STOPPED'. Also, you must check
    that no other job is currently running, because this job may start the
    instance
    """
    return vm.operstate == "STOPPED" and vm.backendjobstatus == "success"


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

    raise faults.NotImplemented('Resize not supported.')


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

    raise faults.NotImplemented('Resize not supported.')


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

    log.info("Get console  VM %s", vm)

    console_type = args.get('type', '')
    if console_type != 'vnc':
        raise faults.BadRequest('Type can only be "vnc".')

    # Use RAPI to get VNC console information for this instance
    if get_rsapi_state(vm) != 'ACTIVE':
        raise faults.BadRequest('Server not in ACTIVE state.')

    if settings.TEST:
        console_data = {'kind': 'vnc', 'host': 'ganeti_node', 'port': 1000}
    else:
        console_data = backend.get_instance_console(vm)

    if console_data['kind'] != 'vnc':
        message = 'got console of kind %s, not "vnc"' % console_data['kind']
        raise faults.ServiceUnavailable(message)

    # Let vncauthproxy decide on the source port.
    # The alternative: static allocation, e.g.
    # sport = console_data['port'] - 1000
    sport = 0
    daddr = console_data['host']
    dport = console_data['port']
    password = random_password()

    if settings.TEST:
        fwd = {'source_port': 1234, 'status': 'OK'}
    else:
        fwd = request_vnc_forwarding(sport, daddr, dport, password)

    if fwd['status'] != "OK":
        raise faults.ServiceUnavailable('vncauthproxy returned error status')

    # Verify that the VNC server settings haven't changed
    if not settings.TEST:
        if console_data != backend.get_instance_console(vm):
            raise faults.ServiceUnavailable('VNC Server settings changed.')

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


@server_action('firewallProfile')
def set_firewall_profile(request, vm, args):
    # Normal Response Code: 200
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)

    profile = args.get('profile', '')
    log.info("Set VM %s firewall %s", vm, profile)
    if profile not in [x[0] for x in NetworkInterface.FIREWALL_PROFILES]:
        raise faults.BadRequest("Unsupported firewall profile")
    backend.set_firewall_profile(vm, profile)
    return HttpResponse(status=202)


@network_action('add')
@transaction.commit_on_success
def add(request, net, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       overLimit (413)

    if net.state != 'ACTIVE':
        raise faults.BuildInProgress('Network not active yet')

    server_id = args.get('serverRef', None)
    if not server_id:
        raise faults.BadRequest('Malformed Request.')

    vm = get_vm(server_id, request.user_uniq, non_suspended=True)

    address = None
    if net.dhcp:
        # Get a free IP from the address pool.
        try:
            address = get_network_free_address(net)
        except EmptyPool:
            raise faults.OverLimit('Network is full')

    log.info("Connecting VM %s to Network %s(%s)", vm, net, address)

    backend.connect_to_network(vm, net, address)
    return HttpResponse(status=202)


@network_action('remove')
@transaction.commit_on_success
def remove(request, net, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       overLimit (413)

    try:  # attachment string: nic-<vm-id>-<nic-index>
        server_id = args.get('attachment', None).split('-')[1]
        nic_index = args.get('attachment', None).split('-')[2]
    except AttributeError:
        raise faults.BadRequest("Malformed Request")
    except IndexError:
        raise faults.BadRequest('Malformed Network Interface Id')

    if not server_id or not nic_index:
        raise faults.BadRequest('Malformed Request.')

    vm = get_vm(server_id, request.user_uniq, non_suspended=True)
    nic = get_nic_from_index(vm, nic_index)

    log.info("Removing NIC %s from VM %s", str(nic.index), vm)

    if nic.dirty:
        raise faults.BuildInProgress('Machine is busy.')
    else:
        vm.nics.all().update(dirty=True)

    backend.disconnect_from_network(vm, nic)
    return HttpResponse(status=202)
