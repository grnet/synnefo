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
from synnefo.logic import backend
from synnefo.logic.backend_allocator import BackendAllocator
from synnefo.db.models import (NetworkInterface, VirtualMachine, Network,
                               VirtualMachineMetadata, IPAddress, Subnet)
from synnefo.db import query as db_query

from vncauthproxy.client import request_forwarding as request_vnc_forwarding

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
        raise faults.BadRequest("Can not perform '%s' action while there is a"
                                " pending '%s'." % (action, pending_action))

    # Check if action can be performed to VM's operstate
    operstate = vm.operstate
    if operstate == "BUILD" and action != "BUILD":
        raise faults.BuildInProgress("Server '%s' is being build." % vm.id)
    elif (action == "START" and operstate != "STOPPED") or\
         (action == "STOP" and operstate != "STARTED") or\
         (action == "RESIZE" and operstate != "STOPPED") or\
         (action in ["CONNECT", "DISCONNECT"] and operstate != "STOPPED"
          and not settings.GANETI_USE_HOTPLUG):
        raise faults.BadRequest("Can not perform '%s' action while server is"
                                " in '%s' state." % (action, operstate))
    return


def server_command(action):
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
                    quotas.reject_serial(vm.serial)
                    transaction.commit()
                raise

            if action == "BUILD" and vm.serial is not None:
                # XXX: Special case for server creation: we must accept the
                # commission because the VM has been stored in DB. Also, if
                # communication with Ganeti fails, the job will never reach
                # Ganeti, and the commission will never be resolved.
                quotas.accept_serial(vm.serial)

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
           personality=[], private_networks=None, floating_ips=None,
           use_backend=None):
    if use_backend is None:
        # Allocate server to a Ganeti backend
        use_backend = allocate_new_server(userid, flavor)

    if private_networks is None:
        private_networks = []
    if floating_ips is None:
        floating_ips = []

    # Fix flavor for archipelago
    disk_template, provider = util.get_flavor_provider(flavor)
    if provider:
        flavor.disk_template = disk_template
        flavor.disk_provider = provider
        flavor.disk_origin = None
        if provider == 'vlmc':
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

    nics = create_instance_nics(vm, userid, private_networks, floating_ips)

    for key, val in metadata.items():
        VirtualMachineMetadata.objects.create(
            meta_key=key,
            meta_value=val,
            vm=vm)

    # Create the server in Ganeti.
    vm = create_server(vm, nics, flavor, image, personality, password)

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
    vm.backendjobid = jobID
    vm.save()
    log.info("User %s created VM %s, NICs %s, Backend %s, JobID %s",
             vm.userid, vm, nics, backend, str(jobID))

    return jobID


def create_instance_nics(vm, userid, private_networks=[], floating_ips=[]):
    """Create NICs for VirtualMachine.

    Helper function for allocating IP addresses and creating NICs in the DB
    for a VirtualMachine. Created NICs are the combination of the default
    network policy (defined by administration settings) and the private
    networks defined by the user.

    """
    attachments = []
    for network_id in settings.DEFAULT_INSTANCE_NETWORKS:
        network, ipaddress = None, None
        if network_id == "SNF:ANY_PUBLIC":
            ipaddress = util.allocate_public_address(backend=vm.backend,
                                                     userid=userid)
            network = ipaddress.network
        else:
            try:
                network = Network.objects.get(id=network_id, deleted=False)
            except Network.DoesNotExist:
                msg = "Invalid configuration. Setting"\
                      " 'DEFAULT_INSTANCE_NETWORKS' contains invalid"\
                      " network '%s'" % network_id
                log.error(msg)
                raise Exception(msg)
            try:
                subnet = network.subnets.get(ipversion=4, dhcp=True)
                ipaddress = util.get_network_free_address(subnet, userid)
            except Subnet.DoesNotExist:
                ipaddress = None
        attachments.append((network, ipaddress))
    for address in floating_ips:
        floating_ip = get_floating_ip(userid=vm.userid, address=address)
        attachments.append((floating_ip.network, floating_ip))
    for network_id in private_networks:
        network = util.get_network(network_id, userid, non_deleted=True)
        if network.public:
            raise faults.Forbidden("Can not connect to public network")
        attachments.append((network, ipaddress))

    nics = []
    for index, (network, ipaddress) in enumerate(attachments):
        # Create VM's public NIC. Do not wait notification form ganeti
        # hooks to create this NIC, because if the hooks never run (e.g.
        # building error) the VM's public IP address will never be
        # released!
        nic = NetworkInterface.objects.create(userid=userid, machine=vm,
                                              network=network, index=index,
                                              state="BUILDING")
        if ipaddress is not None:
            ipaddress.nic = nic
            ipaddress.save()
        nics.append(nic)
    return nics


@server_command("DESTROY")
def destroy(vm):
    log.info("Deleting VM %s", vm)
    return backend.delete_instance(vm)


@server_command("START")
def start(vm):
    log.info("Starting VM %s", vm)
    return backend.startup_instance(vm)


@server_command("STOP")
def stop(vm):
    log.info("Stopping VM %s", vm)
    return backend.shutdown_instance(vm)


@server_command("REBOOT")
def reboot(vm, reboot_type):
    if reboot_type not in ("SOFT", "HARD"):
        raise faults.BadRequest("Malformed request. Invalid reboot"
                                " type %s" % reboot_type)
    log.info("Rebooting VM %s. Type %s", vm, reboot_type)

    return backend.reboot_instance(vm, reboot_type.lower())


@server_command("RESIZE")
def resize(vm, flavor):
    old_flavor = vm.flavor
    # User requested the same flavor
    if old_flavor.id == flavor.id:
        raise faults.BadRequest("Server '%s' flavor is already '%s'."
                                % (vm, flavor))
        return None
    # Check that resize can be performed
    if old_flavor.disk != flavor.disk:
        raise faults.BadRequest("Can not resize instance disk.")
    if old_flavor.disk_template != flavor.disk_template:
        raise faults.BadRequest("Can not change instance disk template.")

    log.info("Resizing VM from flavor '%s' to '%s", old_flavor, flavor)
    commission_info = {"cyclades.cpu": flavor.cpu - old_flavor.cpu,
                       "cyclades.ram": 1048576 * (flavor.ram - old_flavor.ram)}
    # Save serial to VM, since it is needed by server_command decorator
    vm.serial = quotas.issue_commission(user=vm.userid,
                                        source=quotas.DEFAULT_SOURCE,
                                        provisions=commission_info,
                                        name="resource: %s. resize" % vm)
    return backend.resize_instance(vm, vcpus=flavor.cpu, memory=flavor.ram)


@server_command("SET_FIREWALL_PROFILE")
def set_firewall_profile(vm, profile, nic):
    log.info("Setting VM %s, NIC %s, firewall %s", vm, nic, profile)

    if profile not in [x[0] for x in NetworkInterface.FIREWALL_PROFILES]:
        raise faults.BadRequest("Unsupported firewall profile")
    backend.set_firewall_profile(vm, profile=profile, nic=nic)
    return None


@server_command("CONNECT")
def connect(vm, network):
    if network.state != 'ACTIVE':
        raise faults.BuildInProgress('Network not active yet')

    address = None
    try:
        subnet = network.subnets.get(ipversion=4, dhcp=True)
        address = util.get_network_free_address(subnet, userid=vm.userid)
    except Subnet.DoesNotExist:
        subnet = None

    nic = NetworkInterface.objects.create(machine=vm, network=network,
                                          state="BUILDING")
    if address is not None:
        address.nic = nic
        address.save()
    log.info("Connecting VM %s to Network %s. NIC: %s", vm, network, nic)

    return backend.connect_to_network(vm, nic)


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

    return console


@server_command("CONNECT")
def add_floating_ip(vm, address):
    floating_ip = get_floating_ip(userid=vm.userid, address=address)
    nic = NetworkInterface.objects.create(machine=vm,
                                          network=floating_ip.network,
                                          ipv4=floating_ip.ipv4,
                                          ip_type="FLOATING",
                                          state="BUILDING")
    log.info("Connecting VM %s to floating IP %s. NIC: %s", vm, floating_ip,
             nic)
    return backend.connect_to_network(vm, nic)


def get_floating_ip(userid, address):
    """Get a floating IP by it's address.

    Helper function for looking up a IPAddress by it's address. This function
    also checks if the floating IP is currently used by any instance.

    """
    try:
        # Get lock in VM, to guarantee that floating IP will only by assigned
        # once
        floating_ip = db_query.get_user_floating_ip(userid=userid,
                                                    address=address,
                                                    for_update=True)
    except IPAddress.DoesNotExist:
        raise faults.ItemNotFound("Floating IP with address '%s' does not"
                                  " exist" % address)

    if floating_ip.nic is not None:
        raise faults.Conflict("Floating IP '%s' already in use" %
                              floating_ip.id)

    return floating_ip


@server_command("DISCONNECT")
def remove_floating_ip(vm, address):
    try:
        floating_ip = db_query.get_server_floating_ip(server=vm,
                                                      address=address,
                                                      for_update=True)
    except IPAddress.DoesNotExist:
        raise faults.BadRequest("Server '%s' has no floating ip with"
                                " address '%s'" % (vm, address))

    nic = floating_ip.nic
    log.info("Removing NIC %s from VM %s. Floating IP '%s'", str(nic.index),
             vm, floating_ip)

    return backend.disconnect_from_network(vm, nic)


def rename(server, new_name):
    """Rename a VirtualMachine."""
    old_name = server.name
    server.name = new_name
    server.save()
    log.info("Renamed server '%s' from '%s' to '%s'", server, old_name,
             new_name)
    return server
