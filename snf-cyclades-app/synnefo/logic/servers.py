# Copyright (C) 2010-2016 GRNET S.A. and individual contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

from datetime import datetime
from socket import getfqdn
from random import choice
from django import dispatch
from synnefo.db import transaction
import json

from snf_django.lib.api import faults
from django.conf import settings
from synnefo.api import util
from synnefo.logic import backend, ips, utils
from synnefo.logic.backend_allocator import BackendAllocator
from synnefo.db.models import (NetworkInterface, VirtualMachine,
                               VirtualMachineMetadata, IPAddressHistory,
                               IPAddress, Network, Image, pooled_rapi_client)
from vncauthproxy.client import request_forwarding as request_vnc_forwarding
from synnefo.logic import rapi
from synnefo.volume.volumes import _create_volume
from synnefo.volume.util import get_volume, assign_volume_to_server
from synnefo.logic import commands
from synnefo import quotas

log = logging.getLogger(__name__)

# server creation signal
server_created = dispatch.Signal(providing_args=["created_vm_params"])


@transaction.commit_on_success
def create(userid, name, password, flavor, image_id, metadata={},
           personality=[], networks=None, use_backend=None, project=None,
           volumes=None, helper=False, user_projects=None,
           shared_to_project=False, key_name=None):

    utils.check_name_length(name, VirtualMachine.VIRTUAL_MACHINE_NAME_LENGTH,
                            "Server name is too long")

    # Get the image, if any, that is used for the first volume
    vol_image_id = None
    if volumes:
        vol = volumes[0]
        if vol["source_type"] in ["image", "snapshot"]:
            vol_image_id = vol["source_uuid"]

    # Check conflict between server's and volume's image
    if image_id and vol_image_id and image_id != vol_image_id:
        raise faults.BadRequest("The specified server's image is different"
                                " from the the source of the first volume.")
    elif vol_image_id and not image_id:
        image_id = vol_image_id
    elif not image_id:
        raise faults.BadRequest("You need to specify either an image or a"
                                " block device mapping.")

    if len(metadata) > settings.CYCLADES_VM_MAX_METADATA:
        raise faults.BadRequest("Virtual Machines cannot have more than %s "
                                "metadata items" %
                                settings.CYCLADES_VM_MAX_METADATA)
    # Get image info
    image = util.get_image_dict(image_id, userid)

    if not volumes:
        # If no volumes are specified, we automatically create a volume with
        # the size of the flavor and filled with the specified image.
        volumes = [{"source_type": "image",
                    "source_uuid": image_id,
                    "size": flavor.disk,
                    "delete_on_termination": True}]
    assert(len(volumes) > 0), "Cannot create server without volumes"

    if volumes[0]["source_type"] == "blank":
        raise faults.BadRequest("Root volume cannot be blank")

    try:
        is_system = (image["owner"] == settings.SYSTEM_IMAGES_OWNER)
        img, created = Image.objects.get_or_create(uuid=image["id"],
                                                   version=image["version"])
        if created:
            img.owner = image["owner"]
            img.name = image["name"]
            img.location = image["location"]
            img.mapfile = image["mapfile"]
            img.is_public = image["is_public"]
            img.is_snapshot = image["is_snapshot"]
            img.is_system = is_system
            img.os = image["metadata"].get("OS", "unknown")
            img.osfamily = image["metadata"].get("OSFAMILY", "unknown")
            img.save()
    except Exception as e:
        # Image info is not critical. Continue if it fails for any reason
        log.warning("Failed to store image info: %s", e)

    if use_backend is None:
        # Allocate server to a Ganeti backend
        use_backend = allocate_new_server(userid, flavor)

    # Create the ports for the server
    ports = create_instance_ports(userid, user_projects, networks)

    if project is None:
        project = userid

    # We must save the VM instance now, so that it gets a valid
    # vm.backend_vm_id.
    vm = VirtualMachine.objects.create(name=name,
                                       backend=use_backend,
                                       userid=userid,
                                       project=project,
                                       shared_to_project=shared_to_project,
                                       imageid=image["id"],
                                       image_version=image["version"],
                                       key_name=key_name,
                                       flavor=flavor,
                                       operstate="BUILD",
                                       helper=helper)
    log.info("Created entry in DB for VM '%s'", vm)

    # Associate the ports with the server
    for index, port in enumerate(ports):
        associate_port_with_machine(port, vm)
        port.index = index
        port.save()

    # Create instance volumes
    server_vtype = flavor.volume_type
    server_volumes = []
    for index, vol_info in enumerate(volumes):
        if vol_info["source_type"] == "volume":
            uuid = vol_info["source_uuid"]
            v = get_volume(userid, user_projects, uuid, for_update=True,
                           non_deleted=True, exception=faults.BadRequest)
            if v.volume_type_id != server_vtype.id:
                msg = ("Volume '%s' has type '%s' while flavor's volume type"
                       " is '%s'" % (v.id, v.volume_type_id, server_vtype.id))
                raise faults.BadRequest(msg)
            if v.status != "AVAILABLE":
                raise faults.BadRequest("Cannot use volume while it is in %s"
                                        " status" % v.status)
            v.delete_on_termination = vol_info["delete_on_termination"]
        else:
            v = _create_volume(user_id=userid, volume_type=server_vtype,
                               project=project, index=index,
                               shared_to_project=shared_to_project,
                               **vol_info)
        assign_volume_to_server(vm, v, index=index)
        server_volumes.append(v)

    # Create instance metadata
    for key, val in metadata.items():
        utils.check_name_length(key, VirtualMachineMetadata.KEY_LENGTH,
                                "Metadata key is too long")
        utils.check_name_length(val, VirtualMachineMetadata.VALUE_LENGTH,
                                "Metadata value is too long")
        VirtualMachineMetadata.objects.create(
            meta_key=key,
            meta_value=val,
            vm=vm)

    public_key = None
    if key_name is not None:
        keypair = util.get_keypair(key_name, userid)
        public_key = keypair.content

    # Create the server in Ganeti.
    vm = create_server(vm, ports, server_volumes, flavor, image, personality,
                       password, public_key)

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


@commands.server_command("BUILD")
def create_server(vm, nics, volumes, flavor, image, personality, password,
                  public_key):
    # dispatch server created signal needed to trigger the 'vmapi', which
    # enriches the vm object with the 'config_url' attribute which must be
    # passed to the Ganeti job.

    # If the root volume has a provider, then inform snf-image to not fill
    # the volume with data
    image_id = image["pithosmap"]
    root_volume = volumes[0]
    if root_volume.volume_type.provider in settings.GANETI_CLONE_PROVIDERS:
        image_id = "null"

    created_vm_params = {
        'img_id': image_id,
        'img_passwd': password,
        'img_format': str(image['format']),
        'img_personality': json.dumps(personality),
        'img_properties': json.dumps(image['metadata']),
    }

    if public_key is not None:
        created_vm_params['auth_keys'] = public_key

    server_created.send(sender=vm, created_vm_params=created_vm_params)

    # send job to Ganeti
    try:
        jobID = backend.create_instance(vm, nics, volumes, flavor, image)
    except:
        log.exception("Failed create instance '%s'", vm)
        jobID = None
        vm.operstate = "ERROR"
        vm.backendlogmsg = "Failed to send job to Ganeti."
        vm.save()
        vm.nics.all().update(state="ERROR")
        vm.volumes.all().update(status="ERROR")

    # At this point the job is enqueued in the Ganeti backend
    vm.backendopcode = "OP_INSTANCE_CREATE"
    vm.backendjobid = jobID
    vm.save()
    log.info("User %s created VM %s, NICs %s, Backend %s, JobID %s",
             vm.userid, vm, nics, vm.backend, str(jobID))

    return jobID


@commands.server_command("DESTROY")
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


@commands.server_command("START")
def start(vm):
    log.info("Starting VM %s", vm)
    return backend.startup_instance(vm)


@commands.server_command("STOP")
def stop(vm, shutdown_timeout=None):
    log.info("Stopping VM %s", vm)
    return backend.shutdown_instance(vm, shutdown_timeout=shutdown_timeout)


@commands.server_command("REBOOT")
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
    comm = commands.server_command("RESIZE", action_fields=action_fields)
    return comm(_resize)(vm, flavor)


def _resize(vm, flavor):
    old_flavor = vm.flavor
    # User requested the same flavor
    if old_flavor.id == flavor.id:
        raise faults.BadRequest("Server '%s' flavor is already '%s'."
                                % (vm, flavor))
    # Check that resize can be performed
    if old_flavor.disk != flavor.disk:
        raise faults.BadRequest("Cannot change instance's disk size.")
    if old_flavor.volume_type_id != flavor.volume_type_id:
        raise faults.BadRequest("Cannot change instance's volume type.")

    log.info("Resizing VM from flavor '%s' to '%s", old_flavor, flavor)
    return backend.resize_instance(vm, vcpus=flavor.cpu, memory=flavor.ram)


@transaction.commit_on_success
def reassign(vm, project, shared_to_project):
    commands.validate_server_action(vm, "REASSIGN")

    if vm.project == project:
        if vm.shared_to_project != shared_to_project:
            log.info("%s VM %s to project %s",
                "Sharing" if shared_to_project else "Unsharing",
                vm, project)
            vm.shared_to_project = shared_to_project
            vm.volumes.filter(index=0, deleted=False)\
                      .update(shared_to_project=shared_to_project)
            vm.save()
    else:
        action_fields = {"to_project": project, "from_project": vm.project}
        log.info("Reassigning VM %s from project %s to %s, shared: %s",
                vm, vm.project, project, shared_to_project)
        vm.project = project
        vm.shared_to_project = shared_to_project
        vm.save()
        vm.volumes.filter(index=0, deleted=False).update(project=project,
            shared_to_project=shared_to_project)
        quotas.issue_and_accept_commission(vm, action="REASSIGN",
                action_fields=action_fields)
    return vm


@commands.server_command("SET_FIREWALL_PROFILE")
def set_firewall_profile(vm, profile, nic):
    log.info("Setting VM %s, NIC %s, firewall %s", vm, nic, profile)

    if profile not in [x[0] for x in NetworkInterface.FIREWALL_PROFILES]:
        raise faults.BadRequest("Unsupported firewall profile")
    backend.set_firewall_profile(vm, profile=profile, nic=nic)
    return None


@commands.server_command("CONNECT")
def connect(vm, network, port=None):
    if port is None:
        port = _create_port(vm.userid, network)
    associate_port_with_machine(port, vm)

    log.info("Creating NIC %s with IPv4 Address %s", port, port.ipv4_address)

    return backend.connect_to_network(vm, port)


@commands.server_command("DISCONNECT")
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

    if vm.operstate != "STARTED":
        raise faults.BadRequest('Server not in ACTIVE state.')

    # Use RAPI to get VNC console information for this instance
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
    def get_console_data(i):
        return {"kind": "vnc",
                "host": i["pnode"],
                "port": i["network_port"]}
    with pooled_rapi_client(vm) as c:
        i = c.GetInstance(vm.backend_vm_id)
    console_data = get_console_data(i)

    if vm.backend.hypervisor == "kvm" and i['hvparams']['serial_console']:
        raise Exception("hv parameter serial_console cannot be true")

    # Check that the instance is really running
    if not i["oper_state"]:
        log.warning("VM '%s' is marked as '%s' in DB while DOWN in Ganeti",
                    vm.id, vm.operstate)
        # Instance is not running. Mock a shutdown job to sync DB
        backend.process_op_status(vm, etime=datetime.now(), jobid=0,
                                  opcode="OP_INSTANCE_SHUTDOWN",
                                  status="success",
                                  logmsg="Reconciliation simulated event")
        raise faults.BadRequest('Server not in ACTIVE state.')

    # Let vncauthproxy decide on the source port.
    # The alternative: static allocation, e.g.
    # sport = console_data['port'] - 1000
    sport = 0
    daddr = console_data['host']
    dport = console_data['port']
    password = util.random_password()

    vnc_extra_opts = settings.CYCLADES_VNCAUTHPROXY_OPTS

    # Maintain backwards compatibility with the dict setting
    if isinstance(vnc_extra_opts, list):
        vnc_extra_opts = choice(vnc_extra_opts)

    fwd = request_vnc_forwarding(sport, daddr, dport, password,
                                 console_type=console_type, **vnc_extra_opts)

    if fwd['status'] != "OK":
        log.error("vncauthproxy returned error status: '%s'" % fwd)
        raise faults.ServiceUnavailable('vncauthproxy returned error status')

    # Verify that the VNC server settings haven't changed
    with pooled_rapi_client(vm) as c:
        i = c.GetInstance(vm.backend_vm_id)
    if get_console_data(i) != console_data:
        raise faults.ServiceUnavailable('VNC Server settings changed.')

    try:
        host = fwd['proxy_address']
    except KeyError:
        host = getfqdn()

    console = {
        'type': console_type,
        'host': host,
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


def show_owner_change(vmid, from_user, to_user):
    return "[OWNER CHANGE vm: %s, from: %s, to: %s]" % (
        vmid, from_user, to_user)


def change_owner(server, new_owner):
    old_owner = server.userid
    server.userid = new_owner
    old_project = server.project
    server.project = new_owner
    server.save()
    log.info("Changed the owner of server '%s' from '%s' to '%s'.",
             server, old_owner, new_owner)
    log.info("Changed the project of server '%s' from '%s' to '%s'.",
             server, old_project, new_owner)
    for vol in server.volumes.filter(
            userid=old_owner).select_for_update():
        vol.userid = new_owner
        vol_old_project = vol.project
        vol.project = new_owner
        vol.save()
        log.info("Changed the owner of volume '%s' from '%s' to '%s'.",
                 vol, old_owner, new_owner)
        log.info("Changed the project of volume '%s' from '%s' to '%s'.",
                 vol, vol_old_project, new_owner)
    for nic in server.nics.filter(userid=old_owner).select_for_update():
        nic.userid = new_owner
        nic.save()
        log.info("Changed the owner of port '%s' from '%s' to '%s'.",
                 nic.id, old_owner, new_owner)
    for ip in IPAddress.objects.filter(nic__machine=server, userid=old_owner).\
            select_for_update().select_related("nic"):
        ips.change_ip_owner(ip, new_owner)
        IPAddressHistory.objects.create(
            server_id=server.id,
            user_id=old_owner,
            network_id=ip.nic.network_id,
            address=ip.address,
            action=IPAddressHistory.DISASSOCIATE,
            action_reason=show_owner_change(server.id, old_owner, new_owner))
        IPAddressHistory.objects.create(
            server_id=server.id,
            user_id=new_owner,
            network_id=ip.nic.network_id,
            address=ip.address,
            action=IPAddressHistory.ASSOCIATE,
            action_reason=show_owner_change(server.id, old_owner, new_owner))


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
                                           public=network.public,
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
    IPAddressHistory if the port has a public IPv4 address from a public
    network.

    """
    if port.machine is not None:
        raise faults.Conflict("Port %s is already in use." % port.id)
    if port.network.public:
        ipv4_address = port.ipv4_address
        if ipv4_address is not None:
            ip_log = IPAddressHistory.objects.create(
                server_id=machine.id,
                user_id=machine.userid,
                network_id=port.network_id,
                address=ipv4_address,
                action=IPAddressHistory.ASSOCIATE,
                action_reason="associate port %s" % port.id
            )
            log.info("Created IP log entry %s", ip_log)
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


def create_instance_ports(user_id, user_projects, networks=None):
    # First connect the instance to the networks defined by the admin
    forced_ports = create_ports_for_setting(user_id, category="admin")
    if networks is None:
        # If the user did not asked for any networks, connect instance to
        # default networks as defined by the admin
        ports = create_ports_for_setting(user_id, category="default")
    else:
        # Else just connect to the networks that the user defined
        ports = create_ports_for_request(user_id, user_projects, networks)
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
        return create_public_ipv4_port(user_id, user_projects=None,
                                       category=category)
    elif network_id == "SNF:ANY_PUBLIC_IPV6":
        return create_public_ipv6_port(user_id, category=category)
    elif network_id == "SNF:ANY_PUBLIC":
        try:
            return create_public_ipv4_port(user_id, user_projects=None,
                                           category=category)
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
            network = util.get_network(network_id, user_id, None,
                                       non_deleted=True)
            return _create_port(user_id, network)
        else:
            raise ValueError("Unknown category: %s" % category)


def create_public_ipv4_port(user_id, user_projects, network=None, address=None,
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
            ipaddress = util.get_floating_ip_by_address(user_id, user_projects,
                                                        address,
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


def create_ports_for_request(user_id, user_projects, networks):
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
    return [_port_for_request(user_id, user_projects, network)
            for network in networks]


def _port_for_request(user_id, user_projects, network_dict):
    if not isinstance(network_dict, dict):
        raise faults.BadRequest("Malformed request. Invalid 'networks' field")
    port_id = network_dict.get("port")
    network_id = network_dict.get("uuid")
    if port_id is not None:
        return util.get_port(port_id, user_id, user_projects, for_update=True)
    elif network_id is not None:
        address = network_dict.get("fixed_ip")
        network = util.get_network(network_id, user_id, user_projects,
                                   non_deleted=True)
        if network.public:
            if network.subnet4 is not None:
                if "fixed_ip" not in network_dict:
                    return create_public_ipv4_port(user_id, user_projects,
                                                   network)
                elif address is None:
                    msg = "Cannot connect to public network"
                    raise faults.BadRequest(msg % network.id)
                else:
                    return create_public_ipv4_port(user_id, user_projects,
                                                   network, address)
            else:
                raise faults.Forbidden("Cannot connect to IPv6 only public"
                                       " network '%s'" % network.id)
        else:
            return _create_port(user_id, network, address=address)
    else:
        raise faults.BadRequest("Network 'uuid' or 'port' attribute"
                                " is required.")
