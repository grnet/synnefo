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

from django.conf import settings
from django.db import transaction

from synnefo.db.models import (VirtualMachine, Network, NetworkInterface,
                                NetworkLink)
from synnefo.logic import utils
from synnefo.util.rapi import GanetiRapiClient


rapi = GanetiRapiClient(*settings.GANETI_CLUSTER_INFO)

_firewall_tags = {
    'ENABLED': settings.GANETI_FIREWALL_ENABLED_TAG,
    'DISABLED': settings.GANETI_FIREWALL_DISABLED_TAG,
    'PROTECTED': settings.GANETI_FIREWALL_PROTECTED_TAG}

_reverse_tags = dict((v.split(':')[3], k) for k, v in _firewall_tags.items())


def process_op_status(vm, jobid, opcode, status, logmsg):
    """Process a job progress notification from the backend

    Process an incoming message from the backend (currently Ganeti).
    Job notifications with a terminating status (sucess, error, or canceled),
    also update the operating state of the VM.

    """
    if (opcode not in [x[0] for x in VirtualMachine.BACKEND_OPCODES] or
       status not in [x[0] for x in VirtualMachine.BACKEND_STATUSES]):
        raise VirtualMachine.InvalidBackendMsgError(opcode, status)

    vm.backendjobid = jobid
    vm.backendjobstatus = status
    vm.backendopcode = opcode
    vm.backendlogmsg = logmsg

    # Notifications of success change the operating state
    if status == 'success' and VirtualMachine.OPER_STATE_FROM_OPCODE[opcode] is not None:
        utils.update_state(vm, VirtualMachine.OPER_STATE_FROM_OPCODE[opcode])
        # Set the deleted flag explicitly, to cater for admin-initiated removals
        if opcode == 'OP_INSTANCE_REMOVE':
            vm.deleted = True

    # Special case: if OP_INSTANCE_CREATE fails --> ERROR
    if status in ('canceled', 'error') and opcode == 'OP_INSTANCE_CREATE':
        utils.update_state(vm, 'ERROR')
    # Any other notification of failure leaves the operating state unchanged

    vm.save()


@transaction.commit_on_success
def process_net_status(vm, nics):
    """Process a net status notification from the backend

    Process an incoming message from the Ganeti backend,
    detailing the NIC configuration of a VM instance.

    Update the state of the VM in the DB accordingly.
    """

    vm.nics.all().delete()
    for i, nic in enumerate(nics):
        if i == 0:
            net = Network.objects.get(public=True)
        else:
            try:
                link = NetworkLink.objects.get(name=nic['link'])
            except NetworkLink.DoesNotExist:
                # Cannot find an instance of NetworkLink for
                # the link attribute specified in the notification
                raise NetworkLink.DoesNotExist("Cannot find a NetworkLink "
                    "object for link='%s'" % nic['link'])
            net = link.network
            if net is None:
                raise Network.DoesNotExist("NetworkLink for link='%s' not "
                    "associated with an existing Network instance." %
                    nic['link'])
    
        firewall = nic.get('firewall', '')
        firewall_profile = _reverse_tags.get(firewall, '')
        if not firewall_profile and net.public:
            firewall_profile = settings.DEFAULT_FIREWALL_PROFILE
    
        vm.nics.create(
            network=net,
            index=i,
            mac=nic.get('mac', ''),
            ipv4=nic.get('ip', ''),
            ipv6=nic.get('ipv6',''),
            firewall_profile=firewall_profile)
    vm.save()


def start_action(vm, action):
    """Update the state of a VM when a new action is initiated."""
    if not action in [x[0] for x in VirtualMachine.ACTIONS]:
        raise VirtualMachine.InvalidActionError(action)

    # No actions to deleted and no actions beside destroy to suspended VMs
    if vm.deleted:
        raise VirtualMachine.DeletedError

    # No actions to machines being built. They may be destroyed, however.
    if vm.operstate == 'BUILD' and action != 'DESTROY':
        raise VirtualMachine.BuildingError

    vm.action = action
    vm.backendjobid = None
    vm.backendopcode = None
    vm.backendjobstatus = None
    vm.backendlogmsg = None

    # Update the relevant flags if the VM is being suspended or destroyed.
    # Do not set the deleted flag here, see ticket #721.
    #
    # The deleted flag is set asynchronously, when an OP_INSTANCE_REMOVE
    # completes successfully. Hence, a server may be visible for some time
    # after a DELETE /servers/id returns HTTP 204.
    #
    if action == "DESTROY":
        # vm.deleted = True
        pass
    elif action == "SUSPEND":
        vm.suspended = True
    elif action == "START":
        vm.suspended = False
    vm.save()


def create_instance(vm, flavor, image, password):

    nic = {'ip': 'pool', 'mode': 'routed', 'link': settings.GANETI_PUBLIC_LINK}

    if settings.IGNORE_FLAVOR_DISK_SIZES:
        if image.backend_id.find("windows") >= 0:
            sz = 14000
        else:
            sz = 4000
    else:
        sz = flavor.disk * 1024

    return rapi.CreateInstance(
        mode='create',
        name=vm.backend_id,
        disk_template='plain',
        disks=[{"size": sz}],     #FIXME: Always ask for a 4GB disk for now
        nics=[nic],
        os=settings.GANETI_OS_PROVIDER,
        ip_check=False,
        name_check=False,
        # Do not specific a node explicitly, have
        # Ganeti use an iallocator instead
        #
        # pnode=rapi.GetNodes()[0],
        dry_run=settings.TEST,
        beparams=dict(auto_balance=True, vcpus=flavor.cpu, memory=flavor.ram),
        osparams=dict(img_id=image.backend_id, img_passwd=password,
                      img_format=image.format),
        # Be explicit about setting serial_console = False for Synnefo-based
        # instances regardless of the cluster-wide setting, see #785
        hvparams=dict(serial_console=False))


def delete_instance(vm):
    start_action(vm, 'DESTROY')
    rapi.DeleteInstance(vm.backend_id, dry_run=settings.TEST)
    vm.nics.all().delete()


def reboot_instance(vm, reboot_type):
    assert reboot_type in ('soft', 'hard')
    rapi.RebootInstance(vm.backend_id, reboot_type, dry_run=settings.TEST)


def startup_instance(vm):
    start_action(vm, 'START')
    rapi.StartupInstance(vm.backend_id, dry_run=settings.TEST)


def shutdown_instance(vm):
    start_action(vm, 'STOP')
    rapi.ShutdownInstance(vm.backend_id, dry_run=settings.TEST)


def get_instance_console(vm):
    # RAPI GetInstanceConsole() returns endpoints to the vnc_bind_address,
    # which is a cluster-wide setting, either 0.0.0.0 or 127.0.0.1, and pretty
    # useless (see #783).
    #
    # Until this is fixed on the Ganeti side, construct a console info reply
    # directly.
    # 
    # WARNING: This assumes that VNC runs on port network_port on
    #          the instance's primary node, and is probably
    #          hypervisor-specific.
    #
    console = {}
    console['kind'] = 'vnc'
    i = rapi.GetInstance(vm.backend_id)
    if i['hvparams']['serial_console']:
        raise Exception("hv parameter serial_console cannot be true")
    console['host'] = i['pnode']
    console['port'] = i['network_port']
    
    return console
    # return rapi.GetInstanceConsole(vm.backend_id)

def request_status_update(vm):
    return rapi.GetInstanceInfo(vm.backend_id)


def get_job_status(jobid):
    return rapi.GetJobStatus(jobid)


def update_status(vm, status):
    utils.update_state(vm, status)

def create_network_link():
    try:
        last = NetworkLink.objects.order_by('-index')[0]
        index = last.index + 1
    except IndexError:
        index = 1

    if index <= settings.GANETI_MAX_LINK_NUMBER:
        name = '%s%d' % (settings.GANETI_LINK_PREFIX, index)
        return NetworkLink.objects.create(index=index, name=name,
                                            available=True)
    return None     # All link slots are filled

@transaction.commit_on_success
def create_network(name, owner):
    try:
        link = NetworkLink.objects.filter(available=True)[0]
    except IndexError:
        link = create_network_link()
        if not link:
            return None

    network = Network.objects.create(
        name=name,
        owner=owner,
        state='ACTIVE',
        link=link)

    link.network = network
    link.available = False
    link.save()

    return network

@transaction.commit_on_success
def delete_network(net):
    link = net.link
    if link.name != settings.GANETI_NULL_LINK:
        link.available = True
        link.network = None
        link.save()

    for vm in net.machines.all():
        disconnect_from_network(vm, net)
        vm.save()
    net.state = 'DELETED'
    net.save()

def connect_to_network(vm, net):
    nic = {'mode': 'bridged', 'link': net.link.name}
    rapi.ModifyInstance(vm.backend_id,
        nics=[('add', nic)],
        dry_run=settings.TEST)

def disconnect_from_network(vm, net):
    nics = vm.nics.filter(network__public=False).order_by('index')
    new_nics = [nic for nic in nics if nic.network != net]
    if new_nics == nics:
        return      # Nothing to remove
    ops = [('remove', {})]
    for i, nic in enumerate(new_nics):
        ops.append((i + 1, {
            'mode': 'bridged',
            'link': nic.network.link.name}))
    rapi.ModifyInstance(vm.backend_id, nics=ops, dry_run=settings.TEST)

def set_firewall_profile(vm, profile):
    try:
        tag = _firewall_tags[profile]
    except KeyError:
        raise ValueError("Unsopported Firewall Profile: %s" % profile)

    # Delete all firewall tags
    for t in _firewall_tags.values():
        rapi.DeleteInstanceTags(vm.backend_id, [t], dry_run=settings.TEST)

    rapi.AddInstanceTags(vm.backend_id, [tag], dry_run=settings.TEST)
    
    # XXX NOP ModifyInstance call to force process_net_status to run
    # on the dispatcher
    rapi.ModifyInstance(vm.backend_id, os_name=settings.GANETI_OS_PROVIDER)
