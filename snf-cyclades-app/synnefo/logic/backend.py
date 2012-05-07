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

import json

from logging import getLogger
from django.conf import settings
from django.db import transaction

from synnefo.db.models import (Backend, VirtualMachine, Network, NetworkLink)
from synnefo.logic import utils
from synnefo.util.rapi import GanetiRapiClient



log = getLogger('synnefo.logic')


_firewall_tags = {
    'ENABLED': settings.GANETI_FIREWALL_ENABLED_TAG,
    'DISABLED': settings.GANETI_FIREWALL_DISABLED_TAG,
    'PROTECTED': settings.GANETI_FIREWALL_PROTECTED_TAG}

_reverse_tags = dict((v.split(':')[3], k) for k, v in _firewall_tags.items())


def create_client(hostname, port=5080, username=None, password=None):
    return GanetiRapiClient(hostname=hostname,
                            port=port,
                            username=username,
                            password=password)

@transaction.commit_on_success
def process_op_status(vm, etime, jobid, opcode, status, logmsg):
    """Process a job progress notification from the backend

    Process an incoming message from the backend (currently Ganeti).
    Job notifications with a terminating status (sucess, error, or canceled),
    also update the operating state of the VM.

    """
    # See #1492, #1031, #1111 why this line has been removed
    #if (opcode not in [x[0] for x in VirtualMachine.BACKEND_OPCODES] or
    if status not in [x[0] for x in VirtualMachine.BACKEND_STATUSES]:
        raise VirtualMachine.InvalidBackendMsgError(opcode, status)

    vm.backendjobid = jobid
    vm.backendjobstatus = status
    vm.backendopcode = opcode
    vm.backendlogmsg = logmsg

    # Notifications of success change the operating state
    state_for_success = VirtualMachine.OPER_STATE_FROM_OPCODE.get(opcode, None)
    if status == 'success' and state_for_success is not None:
        utils.update_state(vm, state_for_success)
        # Set the deleted flag explicitly, cater for admin-initiated removals
        if opcode == 'OP_INSTANCE_REMOVE':
            vm.deleted = True
            vm.nics.all().delete()

    # Special case: if OP_INSTANCE_CREATE fails --> ERROR
    if status in ('canceled', 'error') and opcode == 'OP_INSTANCE_CREATE':
        utils.update_state(vm, 'ERROR')

    # Special case: OP_INSTANCE_REMOVE fails for machines in ERROR,
    # when no instance exists at the Ganeti backend.
    # See ticket #799 for all the details.
    #
    if (status == 'error' and opcode == 'OP_INSTANCE_REMOVE' and
        vm.operstate == 'ERROR'):
        vm.deleted = True
        vm.nics.all().delete()

    vm.backendtime = etime
    # Any other notification of failure leaves the operating state unchanged

    vm.save()


@transaction.commit_on_success
def process_net_status(vm, etime, nics):
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
            ipv6=nic.get('ipv6', ''),
            firewall_profile=firewall_profile)

        # network nics modified, update network object
        net.save()

    vm.backendtime = etime
    vm.save()


@transaction.commit_on_success
def process_create_progress(vm, etime, rprogress, wprogress):

    # XXX: This only uses the read progress for now.
    #      Explore whether it would make sense to use the value of wprogress
    #      somewhere.
    percentage = int(rprogress)

    # The percentage may exceed 100%, due to the way
    # snf-progress-monitor tracks bytes read by image handling processes
    percentage = 100 if percentage > 100 else percentage
    if percentage < 0:
        raise ValueError("Percentage cannot be negative")

    # FIXME: log a warning here, see #1033
#   if last_update > percentage:
#       raise ValueError("Build percentage should increase monotonically " \
#                        "(old = %d, new = %d)" % (last_update, percentage))

    # This assumes that no message of type 'ganeti-create-progress' is going to
    # arrive once OP_INSTANCE_CREATE has succeeded for a Ganeti instance and
    # the instance is STARTED.  What if the two messages are processed by two
    # separate dispatcher threads, and the 'ganeti-op-status' message for
    # successful creation gets processed before the 'ganeti-create-progress'
    # message? [vkoukis]
    #
    #if not vm.operstate == 'BUILD':
    #    raise VirtualMachine.IllegalState("VM is not in building state")

    vm.buildpercentage = percentage
    vm.backendtime = etime
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


def create_instance(vm, flavor, image, password, personality):
    """`image` is a dictionary which should contain the keys:
            'backend_id', 'format' and 'metadata'

        metadata value should be a dictionary.
    """
    nic = {'ip': 'pool', 'network': settings.GANETI_PUBLIC_NETWORK}

    if settings.IGNORE_FLAVOR_DISK_SIZES:
        if image['backend_id'].find("windows") >= 0:
            sz = 14000
        else:
            sz = 4000
    else:
        sz = flavor.disk * 1024

    # Handle arguments to CreateInstance() as a dictionary,
    # initialize it based on a deployment-specific value.
    # This enables the administrator to override deployment-specific
    # arguments, such as the disk template to use, name of os provider
    # and hypervisor-specific parameters at will (see Synnefo #785, #835).
    #
    kw = settings.GANETI_CREATEINSTANCE_KWARGS
    kw['mode'] = 'create'
    kw['name'] = vm.backend_vm_id
    # Defined in settings.GANETI_CREATEINSTANCE_KWARGS
    kw['disk_template'] = flavor.disk_template
    kw['disks'] = [{"size": sz}]
    kw['nics'] = [nic]
    # Defined in settings.GANETI_CREATEINSTANCE_KWARGS
    # kw['os'] = settings.GANETI_OS_PROVIDER
    kw['ip_check'] = False
    kw['name_check'] = False
    # Do not specific a node explicitly, have
    # Ganeti use an iallocator instead
    #
    # kw['pnode']=rapi.GetNodes()[0]
    kw['dry_run'] = settings.TEST

    kw['beparams'] = {
        'auto_balance': True,
        'vcpus': flavor.cpu,
        'memory': flavor.ram}

    kw['osparams'] = {
        'img_id': image['backend_id'],
        'img_passwd': password,
        'img_format': image['format']}
    if personality:
        kw['osparams']['img_personality'] = json.dumps(personality)

    kw['osparams']['img_properties'] = json.dumps(image['metadata'])

    # Defined in settings.GANETI_CREATEINSTANCE_KWARGS
    # kw['hvparams'] = dict(serial_console=False)

    return vm.client.CreateInstance(**kw)


def delete_instance(vm):
    start_action(vm, 'DESTROY')
    vm.client.DeleteInstance(vm.backend_vm_id, dry_run=settings.TEST)


def reboot_instance(vm, reboot_type):
    assert reboot_type in ('soft', 'hard')
    vm.client.RebootInstance(vm.backend_vm_id, reboot_type, dry_run=settings.TEST)
    log.info('Rebooting instance %s', vm.backend_vm_id)


def startup_instance(vm):
    start_action(vm, 'START')
    vm.client.StartupInstance(vm.backend_vm_id, dry_run=settings.TEST)


def shutdown_instance(vm):
    start_action(vm, 'STOP')
    vm.client.ShutdownInstance(vm.backend_vm_id, dry_run=settings.TEST)


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
    i = vm.client.GetInstance(vm.backend_vm_id)
    if i['hvparams']['serial_console']:
        raise Exception("hv parameter serial_console cannot be true")
    console['host'] = i['pnode']
    console['port'] = i['network_port']

    return console
    # return rapi.GetInstanceConsole(vm.backend_vm_id)


def request_status_update(vm):
    return vm.client.GetInstanceInfo(vm.backend_vm_id)


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
def create_network(name, user_id):
    try:
        link = NetworkLink.objects.filter(available=True)[0]
    except IndexError:
        link = create_network_link()
        if not link:
            raise NetworkLink.NotAvailable

    network = Network.objects.create(
        name=name,
        userid=user_id,
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
    vm.client.ModifyInstance(vm.backend_vm_id, nics=[('add', -1, nic)],
                        hotplug=True, dry_run=settings.TEST)


def disconnect_from_network(vm, net):
    nics = vm.nics.filter(network__public=False).order_by('index')
    ops = [('remove', nic.index, {}) for nic in nics if nic.network == net]
    if not ops:  # Vm not connected to network
        return
    vm.client.ModifyInstance(vm.backend_vm_id, nics=ops[::-1],
                        hotplug=True, dry_run=settings.TEST)


def set_firewall_profile(vm, profile):
    try:
        tag = _firewall_tags[profile]
    except KeyError:
        raise ValueError("Unsopported Firewall Profile: %s" % profile)

    client = vm.client
    # Delete all firewall tags
    for t in _firewall_tags.values():
        client.DeleteInstanceTags(vm.backend_vm_id, [t], dry_run=settings.TEST)

    client.AddInstanceTags(vm.backend_vm_id, [tag], dry_run=settings.TEST)

    # XXX NOP ModifyInstance call to force process_net_status to run
    # on the dispatcher
    vm.client.ModifyInstance(vm.backend_vm_id,
                        os_name=settings.GANETI_CREATEINSTANCE_KWARGS['os'])


def get_ganeti_instances(backend=None, bulk=False):
    Instances = [c.client.GetInstances(bulk=bulk) for c in get_backends(backend)]
    return reduce(list.__add__, Instances, [])


def get_ganeti_nodes(backend=None, bulk=False):
    Nodes = [c.client.GetNodes(bulk=bulk) for c in get_backends(backend)]
    return reduce(list.__add__, Nodes, [])


def get_ganeti_jobs(backend=None, bulk=False):
    Jobs = [c.client.GetJobs(bulk=bulk) for c in get_backends(backend)]
    return reduce(list.__add__, Jobs, [])

##
##
##
def get_backends(backend=None):
    if backend:
        return [backend]
    return Backend.objects.all()





