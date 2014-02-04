# Copyright 2011-2014 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

import logging

from socket import getfqdn
from functools import wraps
from django import dispatch
from django.db import transaction
from django.utils import simplejson as json

from snf_django.lib.api import faults
from django.conf import settings
from synnefo import quotas
from synnefo.api import util
from synnefo.logic import backend, ips, utils
from synnefo.logic.backend_allocator import BackendAllocator
from synnefo.db.models import (NetworkInterface, VirtualMachine,
                               VirtualMachineMetadata, IPAddressLog, Network)
from vncauthproxy.client import request_forwarding as request_vnc_forwarding
from synnefo.logic import rapi

log = logging.getLogger(__name__)

# server creation signal
server_created = dispatch.Signal(providing_args=["created_vm_params"])


def validate_server_action(vm, action):
    if vm.deleted:
        raise faults.BadRequest("Server '%s' has been deleted." % vm.id)

    # Destroyin a server should always be permitted
    if action == "DESTROY":
        return

    # Check that there is no pending action
    pending_action = vm.task
    if pending_action:
        if pending_action == "BUILD":
            raise faults.BuildInProgress("Server '%s' is being build." % vm.id)
        raise faults.BadRequest("Cannot perform '%s' action while there is a"
                                " pending '%s'." % (action, pending_action))

    # Check if action can be performed to VM's operstate
    operstate = vm.operstate
    if operstate == "ERROR":
        raise faults.BadRequest("Cannot perform '%s' action while server is"
                                " in 'ERROR' state." % action)
    elif operstate == "BUILD" and action != "BUILD":
        raise faults.BuildInProgress("Server '%s' is being build." % vm.id)
    elif (action == "START" and operstate != "STOPPED") or\
         (action == "STOP" and operstate != "STARTED") or\
         (action == "RESIZE" and operstate != "STOPPED") or\
         (action in ["CONNECT", "DISCONNECT"] and operstate != "STOPPED"
          and not settings.GANETI_USE_HOTPLUG):
        raise faults.BadRequest("Cannot perform '%s' action while server is"
                                " in '%s' state." % (action, operstate))
    return


def server_command(action, action_fields=None):
    """Handle execution of a server action.

    Helper function to validate and execute a server action, handle quota
    commission and update the 'task' of the VM in the DB.

    1) Check if action can be performed. If it can, then there must be no
       pending task (with the exception of DESTROY).
    2) Handle previous commission if unresolved:
       * If it is not pending and it to accept, then accept
       * If it is not pending and to reject or is pending then reject it. Since
       the action can be performed only if there is no pending task, then there
       can be no pending commission. The exception is DESTROY, but in this case
       the commission can safely be rejected, and the dispatcher will generate
       the correct ones!
    3) Issue new commission and associate it with the VM. Also clear the task.
    4) Send job to ganeti
    5) Update task and commit
    """
    def decorator(func):
        @wraps(func)
        @transaction.commit_on_success
        def wrapper(vm, *args, **kwargs):
            user_id = vm.userid
            validate_server_action(vm, action)
            vm.action = action

            commission_name = "client: api, resource: %s" % vm
            quotas.handle_resource_commission(vm, action=action,
                                              action_fields=action_fields,
                                              commission_name=commission_name)
            vm.save()

            # XXX: Special case for server creation!
            if action == "BUILD":
                # Perform a commit, because the VirtualMachine must be saved to
                # DB before the OP_INSTANCE_CREATE job in enqueued in Ganeti.
                # Otherwise, messages will arrive from snf-dispatcher about
                # this instance, before the VM is stored in DB.
                transaction.commit()
                # After committing the locks are released. Refetch the instance
                # to guarantee x-lock.
                vm = VirtualMachine.objects.select_for_update().get(id=vm.id)

            # Send the job to Ganeti and get the associated jobID
            try:
                job_id = func(vm, *args, **kwargs)
            except Exception as e:
                if vm.serial is not None:
                    # Since the job never reached Ganeti, reject the commission
                    log.debug("Rejecting commission: '%s', could not perform"
                              " action '%s': %s" % (vm.serial,  action, e))
                    transaction.rollback()
                    quotas.reject_resource_serial(vm)
                    transaction.commit()
                raise

            if action == "BUILD" and vm.serial is not None:
                # XXX: Special case for server creation: we must accept the
                # commission because the VM has been stored in DB. Also, if
                # communication with Ganeti fails, the job will never reach
                # Ganeti, and the commission will never be resolved.
                quotas.accept_resource_serial(vm)

            log.info("user: %s, vm: %s, action: %s, job_id: %s, serial: %s",
                     user_id, vm.id, action, job_id, vm.serial)

            # store the new task in the VM
            if job_id is not None:
                vm.task = action
                vm.task_job_id = job_id
            vm.save()

            return vm
        return wrapper
    return decorator


@transaction.commit_on_success
def create(userid, name, password, flavor, image, metadata={},
           personality=[], networks=None, use_backend=None):
    if use_backend is None:
        # Allocate server to a Ganeti backend
        use_backend = allocate_new_server(userid, flavor)

    utils.check_name_length(name, VirtualMachine.VIRTUAL_MACHINE_NAME_LENGTH,
                            "Server name is too long")

    # Create the ports for the server
    ports = create_instance_ports(userid, networks)

    # Fix flavor for archipelago
    disk_template, provider = util.get_flavor_provider(flavor)
    if provider:
        flavor.disk_template = disk_template
        flavor.disk_provider = provider
        flavor.disk_origin = None
        if provider in settings.GANETI_CLONE_PROVIDERS:
            flavor.disk_origin = image['checksum']
            image['backend_id'] = 'null'
    else:
        flavor.disk_provider = None

    # We must save the VM instance now, so that it gets a valid
    # vm.backend_vm_id.
    vm = VirtualMachine.objects.create(name=name,
                                       backend=use_backend,
                                       userid=userid,
                                       imageid=image["id"],
                                       flavor=flavor,
                                       operstate="BUILD")
    log.info("Created entry in DB for VM '%s'", vm)

    # Associate the ports with the server
    for index, port in enumerate(ports):
        associate_port_with_machine(port, vm)
        port.index = index
        port.save()

    for key, val in metadata.items():
        utils.check_name_length(key, VirtualMachineMetadata.KEY_LENGTH,
                                "Metadata key is too long")
        utils.check_name_length(val, VirtualMachineMetadata.VALUE_LENGTH,
                                "Metadata value is too long")
        VirtualMachineMetadata.objects.create(
            meta_key=key,
            meta_value=val,
            vm=vm)

    # Create the server in Ganeti.
    vm = create_server(vm, ports, flavor, image, personality, password)

    return vm


@transaction.commit_on_success
def allocate_new_server(userid, flavor):
    """Allocate a new server to a Ganeti backend.

    Allocation is performed based on the owner of the server and the specified
    flavor. Also, backends that do not have a public IPv4 address are excluded
    from server allocation.

    This function runs inside a transaction, because after allocating the
    instance a commit must be performed in order to release all locks.

    """
    backend_allocator = BackendAllocator()
    use_backend = backend_allocator.allocate(userid, flavor)
    if use_backend is None:
        log.error("No available backend for VM with flavor %s", flavor)
        raise faults.ServiceUnavailable("No available backends")
    return use_backend


@server_command("BUILD")
def create_server(vm, nics, flavor, image, personality, password):
    # dispatch server created signal needed to trigger the 'vmapi', which
    # enriches the vm object with the 'config_url' attribute which must be
    # passed to the Ganeti job.
    server_created.send(sender=vm, created_vm_params={
        'img_id': image['backend_id'],
        'img_passwd': password,
        'img_format': str(image['format']),
        'img_personality': json.dumps(personality),
        'img_properties': json.dumps(image['metadata']),
    })
    # send job to Ganeti
    try:
        jobID = backend.create_instance(vm, nics, flavor, image)
    except:
        log.exception("Failed create instance '%s'", vm)
        jobID = None
        vm.operstate = "ERROR"
        vm.backendlogmsg = "Failed to send job to Ganeti."
        vm.save()
        vm.nics.all().update(state="ERROR")

    # At this point the job is enqueued in the Ganeti backend
    vm.backendopcode = "OP_INSTANCE_CREATE"
    vm.backendjobid = jobID
    vm.save()
    log.info("User %s created VM %s, NICs %s, Backend %s, JobID %s",
             vm.userid, vm, nics, vm.backend, str(jobID))

    return jobID


@server_command("DESTROY")
def destroy(vm, shutdown_timeout=None):
    # XXX: Workaround for race where OP_INSTANCE_REMOVE starts executing on
    # Ganeti before OP_INSTANCE_CREATE. This will be fixed when
    # OP_INSTANCE_REMOVE supports the 'depends' request attribute.
    if (vm.backendopcode == "OP_INSTANCE_CREATE" and
       vm.backendjobstatus not in rapi.JOB_STATUS_FINALIZED and
       backend.job_is_still_running(vm) and
       not backend.vm_exists_in_backend(vm)):
            raise faults.BuildInProgress("Server is being build")
    log.info("Deleting VM %s", vm)
    return backend.delete_instance(vm, shutdown_timeout=shutdown_timeout)


@server_command("START")
def start(vm):
    log.info("Starting VM %s", vm)
    return backend.startup_instance(vm)


@server_command("STOP")
def stop(vm, shutdown_timeout=None):
    log.info("Stopping VM %s", vm)
    return backend.shutdown_instance(vm, shutdown_timeout=shutdown_timeout)


@server_command("REBOOT")
def reboot(vm, reboot_type, shutdown_timeout=None):
    if reboot_type not in ("SOFT", "HARD"):
        raise faults.BadRequest("Malformed request. Invalid reboot"
                                " type %s" % reboot_type)
    log.info("Rebooting VM %s. Type %s", vm, reboot_type)

    return backend.reboot_instance(vm, reboot_type.lower(),
                                   shutdown_timeout=shutdown_timeout)


def resize(vm, flavor):
    action_fields = {"beparams": {"vcpus": flavor.cpu,
                                  "maxmem": flavor.ram}}
    comm = server_command("RESIZE", action_fields=action_fields)
    return comm(_resize)(vm, flavor)


def _resize(vm, flavor):
    old_flavor = vm.flavor
    # User requested the same flavor
    if old_flavor.id == flavor.id:
        raise faults.BadRequest("Server '%s' flavor is already '%s'."
                                % (vm, flavor))
    # Check that resize can be performed
    if old_flavor.disk != flavor.disk:
        raise faults.BadRequest("Cannot resize instance disk.")
    if old_flavor.disk_template != flavor.disk_template:
        raise faults.BadRequest("Cannot change instance disk template.")

    log.info("Resizing VM from flavor '%s' to '%s", old_flavor, flavor)
    return backend.resize_instance(vm, vcpus=flavor.cpu, memory=flavor.ram)


@server_command("SET_FIREWALL_PROFILE")
def set_firewall_profile(vm, profile, nic):
    log.info("Setting VM %s, NIC %s, firewall %s", vm, nic, profile)

    if profile not in [x[0] for x in NetworkInterface.FIREWALL_PROFILES]:
        raise faults.BadRequest("Unsupported firewall profile")
    backend.set_firewall_profile(vm, profile=profile, nic=nic)
    return None


@server_command("CONNECT")
def connect(vm, network, port=None):
    if port is None:
        port = _create_port(vm.userid, network)
    associate_port_with_machine(port, vm)

    log.info("Creating NIC %s with IPv4 Address %s", port, port.ipv4_address)

    return backend.connect_to_network(vm, port)


@server_command("DISCONNECT")
def disconnect(vm, nic):
    log.info("Removing NIC %s from VM %s", nic, vm)
    return backend.disconnect_from_network(vm, nic)


def console(vm, console_type):
    """Arrange for an OOB console of the specified type

    This method arranges for an OOB console of the specified type.
    Only consoles of type "vnc" are supported for now.

    It uses a running instance of vncauthproxy to setup proper
    VNC forwarding with a random password, then returns the necessary
    VNC connection info to the caller.

    """
    log.info("Get console  VM %s, type %s", vm, console_type)

    # Use RAPI to get VNC console information for this instance
    if vm.operstate != "STARTED":
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
    password = util.random_password()

    if settings.TEST:
        fwd = {'source_port': 1234, 'status': 'OK'}
    else:
        vnc_extra_opts = settings.CYCLADES_VNCAUTHPROXY_OPTS
        fwd = request_vnc_forwarding(sport, daddr, dport, password,
                                     **vnc_extra_opts)

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

    return console


def rename(server, new_name):
    """Rename a VirtualMachine."""
    utils.check_name_length(new_name,
                            VirtualMachine.VIRTUAL_MACHINE_NAME_LENGTH,
                            "Server name is too long")
    old_name = server.name
    server.name = new_name
    server.save()
    log.info("Renamed server '%s' from '%s' to '%s'", server, old_name,
             new_name)
    return server


@transaction.commit_on_success
def create_port(*args, **kwargs):
    vm = kwargs.get("machine", None)
    if vm is None and len(args) >= 3:
        vm = args[2]
    if vm is not None:
        if vm.nics.count() == settings.GANETI_MAX_NICS_PER_INSTANCE:
            raise faults.BadRequest("Maximum ports per server limit reached")
    return _create_port(*args, **kwargs)


def _create_port(userid, network, machine=None, use_ipaddress=None,
                 address=None, name="", security_groups=None,
                 device_owner=None):
    """Create a new port on the specified network.

    Create a new Port(NetworkInterface model) on the specified Network. If
    'machine' is specified, the machine will be connected to the network using
    this port. If 'use_ipaddress' argument is specified, the port will be
    assigned this IPAddress. Otherwise, an IPv4 address from the IPv4 subnet
    will be allocated.

    """
    if network.state != "ACTIVE":
        raise faults.Conflict("Cannot create port while network '%s' is in"
                              " '%s' status" % (network.id, network.state))
    elif network.action == "DESTROY":
        msg = "Cannot create port. Network %s is being deleted."
        raise faults.Conflict(msg % network.id)

    utils.check_name_length(name, NetworkInterface.NETWORK_IFACE_NAME_LENGTH,
                            "Port name is too long")

    ipaddress = None
    if use_ipaddress is not None:
        # Use an existing IPAddress object.
        ipaddress = use_ipaddress
        if ipaddress and (ipaddress.network_id != network.id):
            msg = "IP Address %s does not belong to network %s"
            raise faults.Conflict(msg % (ipaddress.address, network.id))
    else:
        # Do not allow allocation of new IPs if the network is drained
        if network.drained:
            raise faults.Conflict("Cannot create port while network %s is in"
                                  " 'SNF:DRAINED' status" % network.id)
        # If network has IPv4 subnets, try to allocate the address that the
        # the user specified or a random one.
        if network.subnets.filter(ipversion=4).exists():
            ipaddress = ips.allocate_ip(network, userid=userid,
                                        address=address)
        elif address is not None:
            raise faults.BadRequest("Address %s is not a valid IP for the"
                                    " defined network subnets" % address)

    if ipaddress is not None and ipaddress.nic is not None:
        raise faults.Conflict("IP address '%s' is already in use" %
                              ipaddress.address)

    port = NetworkInterface.objects.create(network=network,
                                           state="DOWN",
                                           userid=userid,
                                           device_owner=None,
                                           name=name)

    # add the security groups if any
    if security_groups:
        port.security_groups.add(*security_groups)

    if ipaddress is not None:
        # Associate IPAddress with the Port
        ipaddress.nic = port
        ipaddress.save()

    if machine is not None:
        # Connect port to the instance.
        machine = connect(machine, network, port)
        jobID = machine.task_job_id
        log.info("Created Port %s with IP %s. Ganeti Job: %s",
                 port, ipaddress, jobID)
    else:
        log.info("Created Port %s with IP %s not attached to any instance",
                 port, ipaddress)

    return port


def associate_port_with_machine(port, machine):
    """Associate a Port with a VirtualMachine.

    Associate the port with the VirtualMachine and add an entry to the
    IPAddressLog if the port has a public IPv4 address from a public network.

    """
    if port.machine is not None:
        raise faults.Conflict("Port %s is already in use." % port.id)
    if port.network.public:
        ipv4_address = port.ipv4_address
        if ipv4_address is not None:
            ip_log = IPAddressLog.objects.create(server_id=machine.id,
                                                 network_id=port.network_id,
                                                 address=ipv4_address,
                                                 active=True)
            log.debug("Created IP log entry %s", ip_log)
    port.machine = machine
    port.state = "BUILD"
    port.device_owner = "vm"
    port.save()
    return port


@transaction.commit_on_success
def delete_port(port):
    """Delete a port by removing the NIC card from the instance.

    Send a Job to remove the NIC card from the instance. The port
    will be deleted and the associated IPv4 addressess will be released
    when the job completes successfully.

    """

    vm = port.machine
    if vm is not None and not vm.deleted:
        vm = disconnect(port.machine, port)
        log.info("Removing port %s, Job: %s", port, vm.task_job_id)
    else:
        backend.remove_nic_ips(port)
        port.delete()
        log.info("Removed port %s", port)

    return port


def create_instance_ports(user_id, networks=None):
    # First connect the instance to the networks defined by the admin
    forced_ports = create_ports_for_setting(user_id, category="admin")
    if networks is None:
        # If the user did not asked for any networks, connect instance to
        # default networks as defined by the admin
        ports = create_ports_for_setting(user_id, category="default")
    else:
        # Else just connect to the networks that the user defined
        ports = create_ports_for_request(user_id, networks)
    total_ports = forced_ports + ports
    if len(total_ports) > settings.GANETI_MAX_NICS_PER_INSTANCE:
        raise faults.BadRequest("Maximum ports per server limit reached")
    return total_ports


def create_ports_for_setting(user_id, category):
    if category == "admin":
        network_setting = settings.CYCLADES_FORCED_SERVER_NETWORKS
        exception = faults.ServiceUnavailable
    elif category == "default":
        network_setting = settings.CYCLADES_DEFAULT_SERVER_NETWORKS
        exception = faults.Conflict
    else:
        raise ValueError("Unknown category: %s" % category)

    ports = []
    for network_ids in network_setting:
        # Treat even simple network IDs as group of networks with one network
        if type(network_ids) not in (list, tuple):
            network_ids = [network_ids]

        error_msgs = []
        for network_id in network_ids:
            success = False
            try:
                ports.append(_port_from_setting(user_id, network_id, category))
                # Port successfully created in one of the networks. Skip the
                # the rest.
                success = True
                break
            except faults.Conflict as e:
                if len(network_ids) == 1:
                    raise exception(e.message)
                else:
                    error_msgs.append(e.message)

        if not success:
            if category == "admin":
                log.error("Cannot connect server to forced networks '%s': %s",
                          network_ids, error_msgs)
                raise exception("Cannot connect server to forced server"
                                " networks.")
            else:
                log.debug("Cannot connect server to default networks '%s': %s",
                          network_ids, error_msgs)
                raise exception("Cannot connect server to default server"
                                " networks.")

    return ports


def _port_from_setting(user_id, network_id, category):
    # TODO: Fix this..you need only IPv4 and only IPv6 network
    if network_id == "SNF:ANY_PUBLIC_IPV4":
        return create_public_ipv4_port(user_id, category=category)
    elif network_id == "SNF:ANY_PUBLIC_IPV6":
        return create_public_ipv6_port(user_id, category=category)
    elif network_id == "SNF:ANY_PUBLIC":
        try:
            return create_public_ipv4_port(user_id, category=category)
        except faults.Conflict as e1:
            try:
                return create_public_ipv6_port(user_id, category=category)
            except faults.Conflict as e2:
                log.error("Failed to connect server to a public IPv4 or IPv6"
                          " network. IPv4: %s, IPv6: %s", e1, e2)
                msg = ("Cannot connect server to a public IPv4 or IPv6"
                       " network.")
                raise faults.Conflict(msg)
    else:  # Case of network ID
        if category in ["user", "default"]:
            return _port_for_request(user_id, {"uuid": network_id})
        elif category == "admin":
            network = util.get_network(network_id, user_id, non_deleted=True)
            return _create_port(user_id, network)
        else:
            raise ValueError("Unknown category: %s" % category)


def create_public_ipv4_port(user_id, network=None, address=None,
                            category="user"):
    """Create a port in a public IPv4 network.

    Create a port in a public IPv4 network (that may also have an IPv6
    subnet). If the category is 'user' or 'default' this will try to use
    one of the users floating IPs. If the category is 'admin' will
    create a port to the public network (without floating IPs or quotas).

    """
    if category in ["user", "default"]:
        if address is None:
            ipaddress = ips.get_free_floating_ip(user_id, network)
        else:
            ipaddress = util.get_floating_ip_by_address(user_id, address,
                                                        for_update=True)
    elif category == "admin":
        if network is None:
            ipaddress = ips.allocate_public_ip(user_id)
        else:
            ipaddress = ips.allocate_ip(network, user_id)
    else:
        raise ValueError("Unknown category: %s" % category)
    if network is None:
        network = ipaddress.network
    return _create_port(user_id, network, use_ipaddress=ipaddress)


def create_public_ipv6_port(user_id, category=None):
    """Create a port in a public IPv6 only network."""
    networks = Network.objects.filter(public=True, deleted=False,
                                      drained=False, subnets__ipversion=6)\
                              .exclude(subnets__ipversion=4)
    if networks:
        return _create_port(user_id, networks[0])
    else:
        msg = "No available IPv6 only network!"
        log.error(msg)
        raise faults.Conflict(msg)


def create_ports_for_request(user_id, networks):
    """Create the server ports requested by the user.

    Create the ports for the new servers as requested in the 'networks'
    attribute. The networks attribute contains either a list of network IDs
    ('uuid') or a list of ports IDs ('port'). In case of network IDs, the user
    can also specify an IPv4 address ('fixed_ip'). In order to connect to a
    public network, the 'fixed_ip' attribute must contain the IPv4 address of a
    floating IP. If the network is public but the 'fixed_ip' attribute is not
    specified, the system will automatically reserve one of the users floating
    IPs.

    """
    if not isinstance(networks, list):
        raise faults.BadRequest("Malformed request. Invalid 'networks' field")
    return [_port_for_request(user_id, network) for network in networks]


def _port_for_request(user_id, network_dict):
    if not isinstance(network_dict, dict):
        raise faults.BadRequest("Malformed request. Invalid 'networks' field")
    port_id = network_dict.get("port")
    network_id = network_dict.get("uuid")
    if port_id is not None:
        return util.get_port(port_id, user_id, for_update=True)
    elif network_id is not None:
        address = network_dict.get("fixed_ip")
        network = util.get_network(network_id, user_id, non_deleted=True)
        if network.public:
            if network.subnet4 is not None:
                if not "fixed_ip" in network_dict:
                    return create_public_ipv4_port(user_id, network)
                elif address is None:
                    msg = "Cannot connect to public network"
                    raise faults.BadRequest(msg % network.id)
                else:
                    return create_public_ipv4_port(user_id, network, address)
            else:
                raise faults.Forbidden("Cannot connect to IPv6 only public"
                                       " network '%s'" % network.id)
        else:
            return _create_port(user_id, network, address=address)
    else:
        raise faults.BadRequest("Network 'uuid' or 'port' attribute"
                                " is required.")
