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
from datetime import datetime

from synnefo.db.models import (Backend, VirtualMachine, Network,
                               BackendNetwork, BACKEND_STATUSES)
from synnefo.logic import utils, ippool
from synnefo.api.faults import OverLimit
from synnefo.api.util import backend_public_networks, get_network_free_address
from synnefo.util.rapi import GanetiRapiClient

log = getLogger('synnefo.logic')


_firewall_tags = {
    'ENABLED': settings.GANETI_FIREWALL_ENABLED_TAG,
    'DISABLED': settings.GANETI_FIREWALL_DISABLED_TAG,
    'PROTECTED': settings.GANETI_FIREWALL_PROTECTED_TAG}

_reverse_tags = dict((v.split(':')[3], k) for k, v in _firewall_tags.items())


def create_client(hostname, port=5080, username=None, password=None):
    return GanetiRapiClient(hostname, port, username, password)


@transaction.commit_on_success
def process_op_status(vm, etime, jobid, opcode, status, logmsg):
    """Process a job progress notification from the backend

    Process an incoming message from the backend (currently Ganeti).
    Job notifications with a terminating status (sucess, error, or canceled),
    also update the operating state of the VM.

    """
    # See #1492, #1031, #1111 why this line has been removed
    #if (opcode not in [x[0] for x in VirtualMachine.BACKEND_OPCODES] or
    if status not in [x[0] for x in BACKEND_STATUSES]:
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
            release_instance_nics(vm)
            vm.deleted = True
            vm.nics.all().delete()

    # Special case: if OP_INSTANCE_CREATE fails --> ERROR
    if status in ('canceled', 'error') and opcode == 'OP_INSTANCE_CREATE':
        utils.update_state(vm, 'ERROR')

    # Special case: OP_INSTANCE_REMOVE fails for machines in ERROR,
    # when no instance exists at the Ganeti backend.
    # See ticket #799 for all the details.
    #
    if (status == 'error' and opcode == 'OP_INSTANCE_REMOVE'):
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

    # Release the ips of the old nics. Get back the networks as multiple
    # changes in the same network, must happen in the same Network object,
    # because transaction will be commited only on exit of the function.
    networks = release_instance_nics(vm)

    new_nics = enumerate(nics)
    for i, new_nic in new_nics:
        network = new_nic.get('network', '')
        n = str(network)
        pk = utils.id_from_network_name(n)

        # Get the cached Network or get it from DB
        if pk in networks:
            net = networks[pk]
        else:
            net = Network.objects.select_for_update().get(pk=pk)

        # Get the new nic info
        mac = new_nic.get('mac', '')
        ipv4 = new_nic.get('ip', '')
        ipv6 = new_nic.get('ipv6', '')

        firewall = new_nic.get('firewall', '')
        firewall_profile = _reverse_tags.get(firewall, '')
        if not firewall_profile and net.public:
            firewall_profile = settings.DEFAULT_FIREWALL_PROFILE

        if ipv4:
            net.reserve_address(ipv4)

        vm.nics.create(
            network=net,
            index=i,
            mac=mac,
            ipv4=ipv4,
            ipv6=ipv6,
            firewall_profile=firewall_profile,
            dirty=False)

    vm.backendtime = etime
    vm.save()


def release_instance_nics(vm):
    networks = {}

    for nic in vm.nics.all():
        pk = nic.network.pk
        # Get the cached Network or get it from DB
        if pk in networks:
            net = networks[pk]
        else:
            # Get the network object in exclusive mode in order
            # to guarantee consistency of the address pool
            net = Network.objects.select_for_update().get(pk=pk)
        if nic.ipv4:
            net.release_address(nic.ipv4)
        nic.delete()

    return networks


@transaction.commit_on_success
def process_network_status(back_network, etime, jobid, opcode, status, logmsg):
    if status not in [x[0] for x in BACKEND_STATUSES]:
        return
        #raise Network.InvalidBackendMsgError(opcode, status)

    back_network.backendjobid = jobid
    back_network.backendjobstatus = status
    back_network.backendopcode = opcode
    back_network.backendlogmsg = logmsg

    # Notifications of success change the operating state
    state_for_success = BackendNetwork.OPER_STATE_FROM_OPCODE.get(opcode, None)
    if status == 'success' and state_for_success is not None:
        back_network.operstate = state_for_success
        if opcode == 'OP_NETWORK_REMOVE':
            back_network.deleted = True

    if status in ('canceled', 'error') and opcode == 'OP_NETWORK_CREATE':
        utils.update_state(back_network, 'ERROR')

    if (status == 'error' and opcode == 'OP_NETWORK_REMOVE'):
        back_network.deleted = True
        back_network.operstate = 'DELETED'

    back_network.save()


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


@transaction.commit_on_success
def create_instance(vm, flavor, image, password, personality):
    """`image` is a dictionary which should contain the keys:
            'backend_id', 'format' and 'metadata'

        metadata value should be a dictionary.
    """

    if settings.PUBLIC_ROUTED_USE_POOL:
        (network, address) = allocate_public_address(vm)
        if address is None:
            raise OverLimit("Can not allocate IP for new machine."
                            " Public networks are full.")
        nic = {'ip': address, 'network': network.backend_id}
    else:
        nic = {'ip': 'pool', 'network': network.backend_id}

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

    # Identify if provider parameter should be set in disk options.
    # Current implementation support providers only fo ext template.
    # To select specific provider for an ext template, template name
    # should be formated as `ext_<provider_name>`.
    provider = None
    disk_template = flavor.disk_template
    if flavor.disk_template.startswith("ext"):
        disk_template, provider = flavor.disk_template.split("_", 1)

    kw['disk_template'] = disk_template
    kw['disks'] = [{"size": sz}]
    if provider:
        kw['disks'][0]['provider'] = provider

    kw['nics'] = [nic]
    if settings.GANETI_USE_HOTPLUG:
        kw['hotplug'] = True
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


def allocate_public_address(vm):
    """Allocate a public IP for a vm."""
    for network in backend_public_networks(vm.backend):
        try:
            address = get_network_free_address(network)
            return (network, address)
        except ippool.IPPool.IPPoolExhausted:
            pass
    return (None, None)


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


def create_network(network, backends=None):
    """ Add and connect a network to backends.

    @param network: Network object
    @param backends: List of Backend objects. None defaults to all.

    """
    backend_jobs = _create_network(network, backends)
    connect_network(network, backend_jobs)
    return network


def _create_network(network, backends=None):
    """Add a network to backends.
    @param network: Network object
    @param backends: List of Backend objects. None defaults to all.

    """

    network_type = network.public and 'public' or 'private'
    if not backends:
        backends = Backend.objects.exclude(offline=True)

    tags = network.backend_tag
    if network.dhcp:
        tags.append('nfdhcpd')
    tags = ','.join(tags)

    backend_jobs = []
    for backend in backends:
        try:
            backend_network = BackendNetwork.objects.get(network=network,
                                                         backend=backend)
        except BackendNetwork.DoesNotExist:
            raise Exception("BackendNetwork for network '%s' in backend '%s'"\
                            " does not exist" % (network.id, backend.id))
        job = backend.client.CreateNetwork(
                network_name=network.backend_id,
                network=network.subnet,
                gateway=network.gateway,
                network_type=network_type,
                mac_prefix=backend_network.mac_prefix,
                tags=tags)
        backend_jobs.append((backend, job))

    return backend_jobs


def connect_network(network, backend_jobs=None):
    """Connect a network to all nodegroups.

    @param network: Network object
    @param backend_jobs: List of tuples of the form (Backend, jobs) which are
                         the backends to connect the network and the jobs on
                         which the connect job depends.

    """

    if network.type in ('PUBLIC_ROUTED', 'CUSTOM_ROUTED'):
        mode = 'routed'
    else:
        mode = 'bridged'

    if not backend_jobs:
        backend_jobs = [(backend, []) for backend in
                        Backend.objects.exclude(offline=True)]

    for backend, job in backend_jobs:
        client = backend.client
        for group in client.GetGroups():
            client.ConnectNetwork(network.backend_id, group, mode,
                                  network.link, [job])


def connect_network_group(backend, network, group):
    """Connect a network to a specific nodegroup of a backend.

    """
    if network.type in ('PUBLIC_ROUTED', 'CUSTOM_ROUTED'):
        mode = 'routed'
    else:
        mode = 'bridged'

    return backend.client.ConnectNetwork(network.backend_id, group, mode,
                                         network.link)


def delete_network(network, backends=None):
    """ Disconnect and a remove a network from backends.

    @param network: Network object
    @param backends: List of Backend objects. None defaults to all.

    """
    backend_jobs = disconnect_network(network, backends)
    _delete_network(network, backend_jobs)


def disconnect_network(network, backends=None):
    """Disconnect a network from all nodegroups.

    @param network: Network object
    @param backends: List of Backend objects. None defaults to all.

    """

    if not backends:
        backends = Backend.objects.exclude(offline=True)

    backend_jobs = []
    for backend in backends:
        client = backend.client
        jobs = []
        for group in client.GetGroups():
            job = client.DisconnectNetwork(network.backend_id, group)
            jobs.append(job)
        backend_jobs.append((backend, jobs))

    return backend_jobs


def disconnect_from_network(vm, nic):
    """Disconnect a virtual machine from a network by removing it's nic.

    @param vm: VirtualMachine object
    @param network: Network object

    """

    op = [('remove', nic.index, {})]
    return vm.client.ModifyInstance(vm.backend_vm_id, nics=op,
                                    hotplug=settings.GANETI_USE_HOTPLUG,
                                    dry_run=settings.TEST)


def _delete_network(network, backend_jobs=None):
    if not backend_jobs:
        backend_jobs = [(backend, []) for backend in
                Backend.objects.exclude(offline=True)]
    for backend, jobs in backend_jobs:
        backend.client.DeleteNetwork(network.backend_id, jobs)


def connect_to_network(vm, network, address):
    """Connect a virtual machine to a network.

    @param vm: VirtualMachine object
    @param network: Network object

    """

    # ip = network.dhcp and 'pool' or None

    nic = {'ip': address, 'network': network.backend_id}
    vm.client.ModifyInstance(vm.backend_vm_id, nics=[('add',  nic)],
                             hotplug=settings.GANETI_USE_HOTPLUG,
                             dry_run=settings.TEST)


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
    Instances = [c.client.GetInstances(bulk=bulk)\
                 for c in get_backends(backend)]
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
    return Backend.objects.filter(offline=False)


def get_physical_resources(backend):
    """ Get the physical resources of a backend.

    Get the resources of a backend as reported by the backend (not the db).

    """
    nodes = get_ganeti_nodes(backend, bulk=True)
    attr = ['mfree', 'mtotal', 'dfree', 'dtotal', 'pinst_cnt', 'ctotal']
    res = {}
    for a in attr:
        res[a] = 0
    for n in nodes:
        # Filter out drained, offline and not vm_capable nodes since they will
        # not take part in the vm allocation process
        if n['vm_capable'] and not n['drained'] and not n['offline']\
           and n['cnodes']:
            for a in attr:
                res[a] += int(n[a])
    return res


def update_resources(backend, resources=None):
    """ Update the state of the backend resources in db.

    """

    if not resources:
        resources = get_physical_resources(backend)

    backend.mfree = resources['mfree']
    backend.mtotal = resources['mtotal']
    backend.dfree = resources['dfree']
    backend.dtotal = resources['dtotal']
    backend.pinst_cnt = resources['pinst_cnt']
    backend.ctotal = resources['ctotal']
    backend.updated = datetime.now()
    backend.save()


def get_memory_from_instances(backend):
    """ Get the memory that is used from instances.

    Get the used memory of a backend. Note: This is different for
    the real memory used, due to kvm's memory de-duplication.

    """
    instances = backend.client.GetInstances(bulk=True)
    mem = 0
    for i in instances:
        mem += i['oper_ram']
    return mem

##
## Synchronized operations for reconciliation
##


def create_network_synced(network, backend):
    result = _create_network_synced(network, backend)
    if result[0] != 'success':
        return result
    result = connect_network_synced(network, backend)
    return result


def _create_network_synced(network, backend):
    client = backend.client

    backend_jobs = _create_network(network, [backend])
    (_, job) = backend_jobs[0]
    return wait_for_job(client, job)


def connect_network_synced(network, backend):
    if network.type in ('PUBLIC_ROUTED', 'CUSTOM_ROUTED'):
        mode = 'routed'
    else:
        mode = 'bridged'
    client = backend.client

    for group in client.GetGroups():
        job = client.ConnectNetwork(network.backend_id, group, mode,
                                    network.link)
        result = wait_for_job(client, job)
        if result[0] != 'success':
            return result

    return result


def wait_for_job(client, jobid):
    result = client.WaitForJobChange(jobid, ['status', 'opresult'], None, None)
    status = result['job_info'][0]
    while status not in ['success', 'error', 'cancel']:
        result = client.WaitForJobChange(jobid, ['status', 'opresult'],
                                        [result], None)
        status = result['job_info'][0]

    if status == 'success':
        return (status, None)
    else:
        error = result['job_info'][1]
        return (status, error)
