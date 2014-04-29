# Copyright (C) 2010-2014 GRNET S.A.
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
from django.conf import settings
from django.db import transaction
from django.utils import simplejson as json
from datetime import datetime, timedelta

from synnefo.db.models import (VirtualMachine, Network,
                               BackendNetwork, BACKEND_STATUSES,
                               pooled_rapi_client, VirtualMachineDiagnostic,
                               Flavor, IPAddress, IPAddressLog)
from synnefo.logic import utils, ips
from synnefo import quotas
from synnefo.api.util import release_resource
from synnefo.util.mac2eui64 import mac2eui64
from synnefo.logic import rapi
from synnefo import volume

from logging import getLogger
log = getLogger(__name__)


_firewall_tags = {
    'ENABLED': settings.GANETI_FIREWALL_ENABLED_TAG,
    'DISABLED': settings.GANETI_FIREWALL_DISABLED_TAG,
    'PROTECTED': settings.GANETI_FIREWALL_PROTECTED_TAG}

_reverse_tags = dict((v.split(':')[3], k) for k, v in _firewall_tags.items())

SIMPLE_NIC_FIELDS = ["state", "mac", "network", "firewall_profile", "index"]
COMPLEX_NIC_FIELDS = ["ipv4_address", "ipv6_address"]
NIC_FIELDS = SIMPLE_NIC_FIELDS + COMPLEX_NIC_FIELDS
DISK_FIELDS = ["status", "size", "index"]
UNKNOWN_NIC_PREFIX = "unknown-nic-"
UNKNOWN_DISK_PREFIX = "unknown-disk-"


def handle_vm_quotas(vm, job_id, job_opcode, job_status, job_fields):
    """Handle quotas for updated VirtualMachine.

    Update quotas for the updated VirtualMachine based on the job that run on
    the Ganeti backend. If a commission has been already issued for this job,
    then this commission is just accepted or rejected based on the job status.
    Otherwise, a new commission for the given change is issued, that is also in
    force and auto-accept mode. In this case, previous commissions are
    rejected, since they reflect a previous state of the VM.

    """
    if job_status not in rapi.JOB_STATUS_FINALIZED:
        return vm

    # Check successful completion of a job will trigger any quotable change in
    # the VM state.
    action = utils.get_action_from_opcode(job_opcode, job_fields)
    if action == "BUILD":
        # Quotas for new VMs are automatically accepted by the API
        return vm

    if vm.task_job_id == job_id and vm.serial is not None:
        # Commission for this change has already been issued. So just
        # accept/reject it. Special case is OP_INSTANCE_CREATE, which even
        # if fails, must be accepted, as the user must manually remove the
        # failed server
        serial = vm.serial
        if job_status == rapi.JOB_STATUS_SUCCESS:
            quotas.accept_resource_serial(vm)
        elif job_status in [rapi.JOB_STATUS_ERROR, rapi.JOB_STATUS_CANCELED]:
            log.debug("Job %s failed. Rejecting related serial %s", job_id,
                      serial)
            quotas.reject_resource_serial(vm)
    elif job_status == rapi.JOB_STATUS_SUCCESS:
        commission_info = quotas.get_commission_info(resource=vm,
                                                     action=action,
                                                     action_fields=job_fields)
        if commission_info is not None:
            # Commission for this change has not been issued, or the issued
            # commission was unaware of the current change. Reject all previous
            # commissions and create a new one in forced mode!
            log.debug("Expected job was %s. Processing job %s. "
                      "Attached serial %s",
                      vm.task_job_id, job_id, vm.serial)
            reason = ("client: dispatcher, resource: %s, ganeti_job: %s"
                      % (vm, job_id))
            try:
                serial = quotas.handle_resource_commission(
                    vm, action,
                    action_fields=job_fields,
                    commission_name=reason,
                    force=True,
                    auto_accept=True)
            except:
                log.exception("Error while handling new commission")
                raise
            log.debug("Issued new commission: %s", serial)
    return vm


@transaction.commit_on_success
def process_op_status(vm, etime, jobid, opcode, status, logmsg, nics=None,
                      disks=None, job_fields=None):
    """Process a job progress notification from the backend

    Process an incoming message from the backend (currently Ganeti).
    Job notifications with a terminating status (sucess, error, or canceled),
    also update the operating state of the VM.

    """
    # See #1492, #1031, #1111 why this line has been removed
    #if (opcode not in [x[0] for x in VirtualMachine.BACKEND_OPCODES] or
    if status not in [x[0] for x in BACKEND_STATUSES]:
        raise VirtualMachine.InvalidBackendMsgError(opcode, status)

    if opcode == "OP_INSTANCE_SNAPSHOT":
        for disk_id, disk_info in job_fields.get("disks", []):
            snap_info = json.loads(disk_info["snapshot_info"])
            snap_id = snap_info["snapshot_id"]
            update_snapshot(snap_id, user_id=vm.userid, job_id=jobid,
                            job_status=status, etime=etime)
        return

    vm.backendjobid = jobid
    vm.backendjobstatus = status
    vm.backendopcode = opcode
    vm.backendlogmsg = logmsg

    if status not in rapi.JOB_STATUS_FINALIZED:
        vm.save()
        return

    if job_fields is None:
        job_fields = {}

    new_operstate = None
    new_flavor = None
    state_for_success = VirtualMachine.OPER_STATE_FROM_OPCODE.get(opcode)

    if status == rapi.JOB_STATUS_SUCCESS:
        if state_for_success is not None:
            new_operstate = state_for_success

        beparams = job_fields.get("beparams")
        if beparams:
            cpu = beparams.get("vcpus")
            ram = beparams.get("maxmem")
            new_flavor = find_new_flavor(vm, cpu=cpu, ram=ram)

        # XXX: Update backendtime only for jobs that have been successfully
        # completed, since only these jobs update the state of the VM. Else a
        # "race condition" may occur when a successful job (e.g.
        # OP_INSTANCE_REMOVE) completes before an error job and messages arrive
        # in reversed order.
        vm.backendtime = etime

    if status in rapi.JOB_STATUS_FINALIZED:
        if nics is not None:
            update_vm_nics(vm, nics, etime)
        if disks is not None:
            # XXX: Replace the job fields with mocked changes as produced by
            # the diff between the DB and Ganeti disks. This is required in
            # order to update quotas for disks that changed, but not from this
            # job!
            disk_changes = update_vm_disks(vm, disks, etime)
            job_fields["disks"] = disk_changes

    # Special case: if OP_INSTANCE_CREATE fails --> ERROR
    if opcode == 'OP_INSTANCE_CREATE' and status in (rapi.JOB_STATUS_CANCELED,
                                                     rapi.JOB_STATUS_ERROR):
        new_operstate = "ERROR"
        vm.backendtime = etime
        # Update state of associated attachments
        vm.nics.all().update(state="ERROR")
        vm.volumes.all().update(status="ERROR")
    elif opcode == 'OP_INSTANCE_REMOVE':
        # Special case: OP_INSTANCE_REMOVE fails for machines in ERROR,
        # when no instance exists at the Ganeti backend.
        # See ticket #799 for all the details.
        if (status == rapi.JOB_STATUS_SUCCESS or
           (status == rapi.JOB_STATUS_ERROR and not vm_exists_in_backend(vm))):
            # server has been deleted, so delete the server's attachments
            vm.volumes.all().update(deleted=True, status="DELETED",
                                    machine=None)
            for nic in vm.nics.all():
                # but first release the IP
                remove_nic_ips(nic)
                nic.delete()
            vm.deleted = True
            new_operstate = state_for_success
            vm.backendtime = etime
            status = rapi.JOB_STATUS_SUCCESS

    if status in rapi.JOB_STATUS_FINALIZED:
        # Job is finalized: Handle quotas/commissioning
        vm = handle_vm_quotas(vm, job_id=jobid, job_opcode=opcode,
                              job_status=status, job_fields=job_fields)
        # and clear task fields
        if vm.task_job_id == jobid:
            vm.task = None
            vm.task_job_id = None

    # Update VM's state and flavor after handling of quotas, since computation
    # of quotas depends on these attributes
    if new_operstate is not None:
        vm.operstate = new_operstate
    if new_flavor is not None:
        vm.flavor = new_flavor

    vm.save()


def find_new_flavor(vm, cpu=None, ram=None):
    """Find VM's new flavor based on the new CPU and RAM"""
    if cpu is None and ram is None:
        return None

    old_flavor = vm.flavor
    ram = ram if ram is not None else old_flavor.ram
    cpu = cpu if cpu is not None else old_flavor.cpu
    if cpu == old_flavor.cpu and ram == old_flavor.ram:
        return None

    try:
        new_flavor = Flavor.objects.get(
            cpu=cpu, ram=ram, disk=old_flavor.disk,
            volume_type_id=old_flavor.volume_type_id)
    except Flavor.DoesNotExist:
        raise Exception("There is no flavor to match the instance specs!"
                        " Instance: %s CPU: %s RAM %s: Disk: %s VolumeType: %s"
                        % (vm.backend_vm_id, cpu, ram, old_flavor.disk,
                           old_flavor.volume_type_id))
    log.info("Flavor of VM '%s' changed from '%s' to '%s'", vm,
             old_flavor.name, new_flavor.name)
    return new_flavor


def nics_are_equal(db_nic, gnt_nic):
    """Check if DB and Ganeti NICs are equal."""
    for field in NIC_FIELDS:
        if getattr(db_nic, field) != gnt_nic[field]:
            return False
    return True


def parse_instance_nics(gnt_nics):
    """Parse NICs of a Ganeti instance"""
    nics = []
    for index, gnic in enumerate(gnt_nics):
        nic_name = gnic.get("name", None)
        if nic_name is not None:
            nic_id = utils.id_from_nic_name(nic_name)
        else:
            # Unknown NIC
            nic_id = UNKNOWN_NIC_PREFIX + str(index)

        network_name = gnic.get('network', '')
        network_id = utils.id_from_network_name(network_name)
        network = Network.objects.get(id=network_id)
        subnet6 = network.subnet6

        # Get the new nic info
        mac = gnic.get('mac')
        ipv4 = gnic.get('ip')
        ipv6 = mac2eui64(mac, subnet6.cidr) if subnet6 else None

        firewall = gnic.get('firewall')
        firewall_profile = _reverse_tags.get(firewall)
        if not firewall_profile and network.public:
            firewall_profile = settings.DEFAULT_FIREWALL_PROFILE

        nic_info = {
            'index': index,
            'network': network,
            'mac': mac,
            'ipv4_address': ipv4,
            'ipv6_address': ipv6,
            'firewall_profile': firewall_profile,
            'state': 'ACTIVE'}

        nics.append((nic_id, nic_info))
    return dict(nics)


def update_vm_nics(vm, nics, etime=None):
    """Update VM's NICs to match with the NICs of the Ganeti instance

    This function will update the VM's NICs(update, delete or create) and
    return a list of quotable changes.

    @param vm: The VirtualMachine the NICs belong to
    @type vm: VirtualMachine object
    @param nics: The NICs of the Ganeti instance
    @type nics: List of dictionaries with NIC information
    @param etime: The datetime the Ganeti instance had these NICs
    @type etime: datetime

    @return: List of quotable changes (add/remove NIC) (currently empty list)
    @rtype: List of dictionaries

    """
    ganeti_nics = parse_instance_nics(nics)
    db_nics = dict([(nic.id, nic) for nic in vm.nics.select_related("network")
                                                    .prefetch_related("ips")])

    for nic_name in set(db_nics.keys()) | set(ganeti_nics.keys()):
        db_nic = db_nics.get(nic_name)
        ganeti_nic = ganeti_nics.get(nic_name)
        if ganeti_nic is None:
            if nic_is_stale(vm, nic):
                log.debug("Removing stale NIC '%s'" % db_nic)
                remove_nic_ips(db_nic)
                db_nic.delete()
            else:
                log.info("NIC '%s' is still being created" % db_nic)
        elif db_nic is None:
            msg = ("NIC/%s of VM %s does not exist in DB! Cannot automatically"
                   " fix this issue!" % (nic_name, vm))
            log.error(msg)
            continue
        elif not nics_are_equal(db_nic, ganeti_nic):
            for f in SIMPLE_NIC_FIELDS:
                # Update the NIC in DB with the values from Ganeti NIC
                setattr(db_nic, f, ganeti_nic[f])
                db_nic.save()

            # Special case where the IPv4 address has changed, because you
            # need to release the old IPv4 address and reserve the new one
            gnt_ipv4_address = ganeti_nic["ipv4_address"]
            db_ipv4_address = db_nic.ipv4_address
            if db_ipv4_address != gnt_ipv4_address:
                change_address_of_port(db_nic, vm.userid,
                                       old_address=db_ipv4_address,
                                       new_address=gnt_ipv4_address,
                                       version=4)

            gnt_ipv6_address = ganeti_nic["ipv6_address"]
            db_ipv6_address = db_nic.ipv6_address
            if db_ipv6_address != gnt_ipv6_address:
                change_address_of_port(db_nic, vm.userid,
                                       old_address=db_ipv6_address,
                                       new_address=gnt_ipv6_address,
                                       version=6)

    return []


def remove_nic_ips(nic, version=None):
    """Remove IP addresses associated with a NetworkInterface.

    Remove all IP addresses that are associated with the NetworkInterface
    object, by returning them to the pool and deleting the IPAddress object. If
    the IP is a floating IP, then it is just disassociated from the NIC.
    If version is specified, then only IP addressses of that version will be
    removed.

    """
    for ip in nic.ips.all():
        if version and ip.ipversion != version:
            continue

        # Update the DB table holding the logging of all IP addresses
        terminate_active_ipaddress_log(nic, ip)

        if ip.floating_ip:
            ip.nic = None
            ip.save()
        else:
            # Release the IPv4 address
            ip.release_address()
            ip.delete()


def terminate_active_ipaddress_log(nic, ip):
    """Update DB logging entry for this IP address."""
    if not ip.network.public or nic.machine is None:
        return
    try:
        ip_log, created = \
            IPAddressLog.objects.get_or_create(server_id=nic.machine_id,
                                               network_id=ip.network_id,
                                               address=ip.address,
                                               active=True)
    except IPAddressLog.MultipleObjectsReturned:
        logmsg = ("Multiple active log entries for IP %s, Network %s,"
                  "Server %s. Cannot proceed!"
                  % (ip.address, ip.network, nic.machine))
        log.error(logmsg)
        raise

    if created:
        logmsg = ("No log entry for IP %s, Network %s, Server %s. Created new"
                  " but with wrong creation timestamp."
                  % (ip.address, ip.network, nic.machine))
        log.error(logmsg)
    ip_log.released_at = datetime.now()
    ip_log.active = False
    ip_log.save()


def change_address_of_port(port, userid, old_address, new_address, version):
    """Change."""
    if old_address is not None:
        msg = ("IPv%s Address of server '%s' changed from '%s' to '%s'"
               % (version, port.machine_id, old_address, new_address))
        log.error(msg)

    # Remove the old IP address
    remove_nic_ips(port, version=version)

    if version == 4:
        ipaddress = ips.allocate_ip(port.network, userid, address=new_address)
        ipaddress.nic = port
        ipaddress.save()
    elif version == 6:
        subnet6 = port.network.subnet6
        ipaddress = IPAddress.objects.create(userid=userid,
                                             network=port.network,
                                             subnet=subnet6,
                                             nic=port,
                                             address=new_address,
                                             ipversion=6)
    else:
        raise ValueError("Unknown version: %s" % version)

    # New address log
    ip_log = IPAddressLog.objects.create(server_id=port.machine_id,
                                         network_id=port.network_id,
                                         address=new_address,
                                         active=True)
    log.info("Created IP log entry '%s' for address '%s' to server '%s'",
             ip_log.id, new_address, port.machine_id)

    return ipaddress


def update_vm_disks(vm, disks, etime=None):
    """Update VM's disks to match with the disks of the Ganeti instance

    This function will update the VM's disks(update, delete or create) and
    return a list of quotable changes.

    @param vm: The VirtualMachine the disks belong to
    @type vm: VirtualMachine object
    @param disks: The disks of the Ganeti instance
    @type disks: List of dictionaries with disk information
    @param etime: The datetime the Ganeti instance had these disks
    @type etime: datetime

    @return: List of quotable changes (add/remove disk)
    @rtype: List of dictionaries

    """
    gnt_disks = parse_instance_disks(disks)
    db_disks = dict([(disk.id, disk)
                     for disk in vm.volumes.filter(deleted=False)])

    changes = []
    for disk_name in set(db_disks.keys()) | set(gnt_disks.keys()):
        db_disk = db_disks.get(disk_name)
        gnt_disk = gnt_disks.get(disk_name)
        if gnt_disk is None:
            # Disk exists in DB but not in Ganeti
            if disk_is_stale(vm, disk):
                log.debug("Removing stale disk '%s'" % db_disk)
                db_disk.status = "DELETED"
                db_disk.deleted = True
                db_disk.save()
                changes.append(("remove", db_disk, {}))
            else:
                log.info("disk '%s' is still being created" % db_disk)
        elif db_disk is None:
            # Disk exists in Ganeti but not in DB
            # TODO: Automatically import disk!
            msg = ("disk/%s of VM %s does not exist in DB! Cannot"
                   " automatically fix this issue!" % (disk_name, vm))
            log.error(msg)
            continue
        elif not disks_are_equal(db_disk, gnt_disk):
            # Disk has changed
            if gnt_disk["size"] != db_disk.size:
                # Size of the disk has changed! TODO: Fix flavor!
                size_delta = gnt_disk["size"] - db_disk.size
                changes.append(("modify", db_disk, {"size_delta": size_delta}))
            if db_disk.status == "CREATING":
                # Disk has been created
                changes.append(("add", db_disk, {}))
            # Update the disk in DB with the values from Ganeti disk
            [setattr(db_disk, f, gnt_disk[f]) for f in DISK_FIELDS]
            db_disk.save()

    return changes


def disks_are_equal(db_disk, gnt_disk):
    """Check if DB and Ganeti disks are equal"""
    for field in DISK_FIELDS:
        if getattr(db_disk, field) != gnt_disk[field]:
            return False
    return True


def parse_instance_disks(gnt_disks):
    """Parse disks of a Ganeti instance"""
    disks = []
    for index, gnt_disk in enumerate(gnt_disks):
        disk_name = gnt_disk.get("name", None)
        if disk_name is not None:
            disk_id = utils.id_from_disk_name(disk_name)
        else:  # Unknown disk
            disk_id = UNKNOWN_DISK_PREFIX + str(index)

        disk_info = {
            'index': index,
            'size': gnt_disk["size"] >> 10,  # Size in GB
            'status': "IN_USE"}

        disks.append((disk_id, disk_info))
    return dict(disks)


def update_snapshot(snap_id, user_id, job_id, job_status, etime):
    """Update a snapshot based on result of a Ganeti job."""
    if job_status in rapi.JOB_STATUS_FINALIZED:
        status = rapi.JOB_STATUS_SUCCESS and "AVAILABLE" or "ERROR"
        log.debug("Updating status of snapshot '%s' to '%s'", snap_id, status)
        volume.util.update_snapshot_status(snap_id, user_id, status=status)


@transaction.commit_on_success
def process_network_status(back_network, etime, jobid, opcode, status, logmsg):
    if status not in [x[0] for x in BACKEND_STATUSES]:
        raise Network.InvalidBackendMsgError(opcode, status)

    back_network.backendjobid = jobid
    back_network.backendjobstatus = status
    back_network.backendopcode = opcode
    back_network.backendlogmsg = logmsg

    # Note: Network is already locked!
    network = back_network.network

    # Notifications of success change the operating state
    state_for_success = BackendNetwork.OPER_STATE_FROM_OPCODE.get(opcode, None)
    if status == rapi.JOB_STATUS_SUCCESS and state_for_success is not None:
        back_network.operstate = state_for_success

    if (status in (rapi.JOB_STATUS_CANCELED, rapi.JOB_STATUS_ERROR)
       and opcode == 'OP_NETWORK_ADD'):
        back_network.operstate = 'ERROR'
        back_network.backendtime = etime

    if opcode == 'OP_NETWORK_REMOVE':
        network_is_deleted = (status == rapi.JOB_STATUS_SUCCESS)
        if network_is_deleted or (status == rapi.JOB_STATUS_ERROR and not
                                  network_exists_in_backend(back_network)):
            back_network.operstate = state_for_success
            back_network.deleted = True
            back_network.backendtime = etime

    if status == rapi.JOB_STATUS_SUCCESS:
        back_network.backendtime = etime
    back_network.save()
    # Also you must update the state of the Network!!
    update_network_state(network)


def update_network_state(network):
    """Update the state of a Network based on BackendNetwork states.

    Update the state of a Network based on the operstate of the networks in the
    backends that network exists.

    The state of the network is:
    * ACTIVE: If it is 'ACTIVE' in at least one backend.
    * DELETED: If it is is 'DELETED' in all backends that have been created.

    This function also releases the resources (MAC prefix or Bridge) and the
    quotas for the network.

    """
    if network.deleted:
        # Network has already been deleted. Just assert that state is also
        # DELETED
        if not network.state == "DELETED":
            network.state = "DELETED"
            network.save()
        return

    backend_states = [s.operstate for s in network.backend_networks.all()]
    if not backend_states and network.action != "DESTROY":
        if network.state != "ACTIVE":
            network.state = "ACTIVE"
            network.save()
            return

    # Network is deleted when all BackendNetworks go to "DELETED" operstate
    deleted = reduce(lambda x, y: x == y and "DELETED", backend_states,
                     "DELETED")

    # Release the resources on the deletion of the Network
    if deleted:
        if network.ips.filter(deleted=False, floating_ip=True).exists():
            msg = "Cannot delete network %s! Floating IPs still in use!"
            log.error(msg % network)
            raise Exception(msg % network)
        log.info("Network %r deleted. Releasing link %r mac_prefix %r",
                 network.id, network.mac_prefix, network.link)
        network.deleted = True
        network.state = "DELETED"
        # Undrain the network, otherwise the network state will remain
        # as 'SNF:DRAINED'
        network.drained = False
        if network.mac_prefix:
            if network.FLAVORS[network.flavor]["mac_prefix"] == "pool":
                release_resource(res_type="mac_prefix",
                                 value=network.mac_prefix)
        if network.link:
            if network.FLAVORS[network.flavor]["link"] == "pool":
                release_resource(res_type="bridge", value=network.link)

        # Set all subnets as deleted
        network.subnets.update(deleted=True)
        # And delete the IP pools
        for subnet in network.subnets.all():
            if subnet.ipversion == 4:
                subnet.ip_pools.all().delete()
        # And all the backend networks since there are useless
        network.backend_networks.all().delete()

        # Issue commission
        if network.userid:
            quotas.issue_and_accept_commission(network, action="DESTROY")
            # the above has already saved the object and committed;
            # a second save would override others' changes, since the
            # object is now unlocked
            return
        elif not network.public:
            log.warning("Network %s does not have an owner!", network.id)
    network.save()


@transaction.commit_on_success
def process_network_modify(back_network, etime, jobid, opcode, status,
                           job_fields):
    assert (opcode == "OP_NETWORK_SET_PARAMS")
    if status not in [x[0] for x in BACKEND_STATUSES]:
        raise Network.InvalidBackendMsgError(opcode, status)

    back_network.backendjobid = jobid
    back_network.backendjobstatus = status
    back_network.opcode = opcode

    add_reserved_ips = job_fields.get("add_reserved_ips")
    if add_reserved_ips:
        network = back_network.network
        for ip in add_reserved_ips:
            network.reserve_address(ip, external=True)

    if status == rapi.JOB_STATUS_SUCCESS:
        back_network.backendtime = etime
    back_network.save()


@transaction.commit_on_success
def process_create_progress(vm, etime, progress):

    percentage = int(progress)

    # The percentage may exceed 100%, due to the way
    # snf-image:copy-progress tracks bytes read by image handling processes
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


@transaction.commit_on_success
def create_instance_diagnostic(vm, message, source, level="DEBUG", etime=None,
                               details=None):
    """
    Create virtual machine instance diagnostic entry.

    :param vm: VirtualMachine instance to create diagnostic for.
    :param message: Diagnostic message.
    :param source: Diagnostic source identifier (e.g. image-helper).
    :param level: Diagnostic level (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
    :param etime: The time the message occured (if available).
    :param details: Additional details or debug information.
    """
    VirtualMachineDiagnostic.objects.create_for_vm(vm, level, source=source,
                                                   source_date=etime,
                                                   message=message,
                                                   details=details)


def create_instance(vm, nics, volumes, flavor, image):
    """`image` is a dictionary which should contain the keys:
            'backend_id', 'format' and 'metadata'

        metadata value should be a dictionary.
    """

    # Handle arguments to CreateInstance() as a dictionary,
    # initialize it based on a deployment-specific value.
    # This enables the administrator to override deployment-specific
    # arguments, such as the disk template to use, name of os provider
    # and hypervisor-specific parameters at will (see Synnefo #785, #835).
    #
    kw = vm.backend.get_create_params()
    kw['mode'] = 'create'
    kw['name'] = vm.backend_vm_id
    # Defined in settings.GANETI_CREATEINSTANCE_KWARGS

    kw['disk_template'] = volumes[0].volume_type.template
    disks = []
    for volume in volumes:
        disk = {"name": volume.backend_volume_uuid,
                "size": volume.size * 1024}
        provider = volume.volume_type.provider
        if provider is not None:
            disk["provider"] = provider
            disk["origin"] = volume.origin
            extra_disk_params = settings.GANETI_DISK_PROVIDER_KWARGS\
                                        .get(provider)
            if extra_disk_params is not None:
                disk.update(extra_disk_params)
        disks.append(disk)

    kw["disks"] = disks

    kw['nics'] = [{"name": nic.backend_uuid,
                   "network": nic.network.backend_id,
                   "ip": nic.ipv4_address}
                  for nic in nics]

    backend = vm.backend
    depend_jobs = []
    for nic in nics:
        bnet, job_ids = ensure_network_is_active(backend, nic.network_id)
        depend_jobs.extend(job_ids)

    kw["depends"] = create_job_dependencies(depend_jobs)

    # Defined in settings.GANETI_CREATEINSTANCE_KWARGS
    # kw['os'] = settings.GANETI_OS_PROVIDER
    kw['ip_check'] = False
    kw['name_check'] = False

    # Do not specific a node explicitly, have
    # Ganeti use an iallocator instead
    #kw['pnode'] = rapi.GetNodes()[0]

    kw['dry_run'] = settings.TEST

    kw['beparams'] = {
        'auto_balance': True,
        'vcpus': flavor.cpu,
        'memory': flavor.ram}

    kw['osparams'] = {
        'config_url': vm.config_url,
        # Store image id and format to Ganeti
        'img_id': image['backend_id'],
        'img_format': image['format']}

    # Use opportunistic locking
    kw['opportunistic_locking'] = settings.GANETI_USE_OPPORTUNISTIC_LOCKING

    # Defined in settings.GANETI_CREATEINSTANCE_KWARGS
    # kw['hvparams'] = dict(serial_console=False)

    log.debug("Creating instance %s", utils.hide_pass(kw))
    with pooled_rapi_client(vm) as client:
        return client.CreateInstance(**kw)


def delete_instance(vm, shutdown_timeout=None):
    with pooled_rapi_client(vm) as client:
        return client.DeleteInstance(vm.backend_vm_id,
                                     shutdown_timeout=shutdown_timeout,
                                     dry_run=settings.TEST)


def reboot_instance(vm, reboot_type, shutdown_timeout=None):
    assert reboot_type in ('soft', 'hard')
    # Note that reboot type of Ganeti job must be always hard. The 'soft' and
    # 'hard' type of OS API is different from the one in Ganeti, and maps to
    # 'shutdown_timeout'.
    kwargs = {"instance": vm.backend_vm_id,
              "reboot_type": "hard"}
    # 'shutdown_timeout' parameter is only support from snf-ganeti>=2.8.2 and
    # Ganeti > 2.10. In other versions this parameter will be ignored and
    # we will fallback to default timeout of Ganeti (120s).
    if shutdown_timeout is not None:
        kwargs["shutdown_timeout"] = shutdown_timeout
    if reboot_type == "hard":
        kwargs["shutdown_timeout"] = 0
    if settings.TEST:
        kwargs["dry_run"] = True
    with pooled_rapi_client(vm) as client:
        return client.RebootInstance(**kwargs)


def startup_instance(vm):
    with pooled_rapi_client(vm) as client:
        return client.StartupInstance(vm.backend_vm_id, dry_run=settings.TEST)


def shutdown_instance(vm, shutdown_timeout=None):
    with pooled_rapi_client(vm) as client:
        return client.ShutdownInstance(vm.backend_vm_id,
                                       timeout=shutdown_timeout,
                                       dry_run=settings.TEST)


def resize_instance(vm, vcpus, memory):
    beparams = {"vcpus": int(vcpus),
                "minmem": int(memory),
                "maxmem": int(memory)}
    with pooled_rapi_client(vm) as client:
        return client.ModifyInstance(vm.backend_vm_id, beparams=beparams)


def get_instance_info(vm):
    with pooled_rapi_client(vm) as client:
        return client.GetInstance(vm.backend_vm_id)


def vm_exists_in_backend(vm):
    try:
        get_instance_info(vm)
        return True
    except rapi.GanetiApiError as e:
        if e.code == 404:
            return False
        raise e


def get_network_info(backend_network):
    with pooled_rapi_client(backend_network) as client:
        return client.GetNetwork(backend_network.network.backend_id)


def network_exists_in_backend(backend_network):
    try:
        get_network_info(backend_network)
        return True
    except rapi.GanetiApiError as e:
        if e.code == 404:
            return False


def job_is_still_running(vm, job_id=None):
    with pooled_rapi_client(vm) as c:
        try:
            if job_id is None:
                job_id = vm.backendjobid
            job_info = c.GetJobStatus(job_id)
            return not (job_info["status"] in rapi.JOB_STATUS_FINALIZED)
        except rapi.GanetiApiError:
            return False


def disk_is_stale(vm, disk, timeout=60):
    """Check if a disk is stale or exists in the Ganeti backend."""
    # First check the state of the disk
    if disk.status == "CREATING":
        if datetime.now() < disk.created + timedelta(seconds=timeout):
            # Do not check for too recent disks to avoid the time overhead
            return False
        if job_is_still_running(vm, job_id=disk.backendjobid):
            return False
        else:
            # If job has finished, check that the disk exists, because the
            # message may have been lost or stuck in the queue.
            vm_info = get_instance_info(vm)
            if disk.backend_volume_uuid in vm_info["disk.names"]:
                return False
    return True


def nic_is_stale(vm, nic, timeout=60):
    """Check if a NIC is stale or exists in the Ganeti backend."""
    # First check the state of the NIC and if there is a pending CONNECT
    if nic.state == "BUILD" and vm.task == "CONNECT":
        if datetime.now() < nic.created + timedelta(seconds=timeout):
            # Do not check for too recent NICs to avoid the time overhead
            return False
        if job_is_still_running(vm, job_id=vm.task_job_id):
            return False
        else:
            # If job has finished, check that the NIC exists, because the
            # message may have been lost or stuck in the queue.
            vm_info = get_instance_info(vm)
            if nic.backend_uuid in vm_info["nic.names"]:
                return False
    return True


def ensure_network_is_active(backend, network_id):
    """Ensure that a network is active in the specified backend

    Check that a network exists and is active in the specified backend. If not
    (re-)create the network. Return the corresponding BackendNetwork object
    and the IDs of the Ganeti job to create the network.

    """
    job_ids = []
    try:
        bnet = BackendNetwork.objects.select_related("network")\
                                     .get(backend=backend, network=network_id)
        if bnet.operstate != "ACTIVE":
            job_ids = create_network(bnet.network, backend, connect=True)
    except BackendNetwork.DoesNotExist:
        network = Network.objects.select_for_update().get(id=network_id)
        bnet = BackendNetwork.objects.create(backend=backend, network=network)
        job_ids = create_network(network, backend, connect=True)

    return bnet, job_ids


def create_network(network, backend, connect=True):
    """Create a network in a Ganeti backend"""
    log.debug("Creating network %s in backend %s", network, backend)

    job_id = _create_network(network, backend)

    if connect:
        job_ids = connect_network(network, backend, depends=[job_id])
        return job_ids
    else:
        return [job_id]


def _create_network(network, backend):
    """Create a network."""

    tags = network.backend_tag
    subnet = None
    subnet6 = None
    gateway = None
    gateway6 = None
    for _subnet in network.subnets.all():
        if _subnet.dhcp and not "nfdhcpd" in tags:
            tags.append("nfdhcpd")
        if _subnet.ipversion == 4:
            subnet = _subnet.cidr
            gateway = _subnet.gateway
        elif _subnet.ipversion == 6:
            subnet6 = _subnet.cidr
            gateway6 = _subnet.gateway

    conflicts_check = False
    if network.public:
        tags.append('public')
        if subnet is not None:
            conflicts_check = True
    else:
        tags.append('private')

    # Use a dummy network subnet for IPv6 only networks. Currently Ganeti does
    # not support IPv6 only networks. To bypass this limitation, we create the
    # network with a dummy network subnet, and make Cyclades connect instances
    # to such networks, with address=None.
    if subnet is None:
        subnet = "10.0.0.0/29"

    try:
        bn = BackendNetwork.objects.get(network=network, backend=backend)
        mac_prefix = bn.mac_prefix
    except BackendNetwork.DoesNotExist:
        raise Exception("BackendNetwork for network '%s' in backend '%s'"
                        " does not exist" % (network.id, backend.id))

    with pooled_rapi_client(backend) as client:
        return client.CreateNetwork(network_name=network.backend_id,
                                    network=subnet,
                                    network6=subnet6,
                                    gateway=gateway,
                                    gateway6=gateway6,
                                    mac_prefix=mac_prefix,
                                    conflicts_check=conflicts_check,
                                    tags=tags)


def connect_network(network, backend, depends=[], group=None):
    """Connect a network to nodegroups."""
    log.debug("Connecting network %s to backend %s", network, backend)

    conflicts_check = False
    if network.public and (network.subnet4 is not None):
        conflicts_check = True

    depends = create_job_dependencies(depends)
    with pooled_rapi_client(backend) as client:
        groups = [group] if group is not None else client.GetGroups()
        job_ids = []
        for group in groups:
            job_id = client.ConnectNetwork(network.backend_id, group,
                                           network.mode, network.link,
                                           conflicts_check,
                                           depends=depends)
            job_ids.append(job_id)
    return job_ids


def delete_network(network, backend, disconnect=True):
    log.debug("Deleting network %s from backend %s", network, backend)

    depends = []
    if disconnect:
        depends = disconnect_network(network, backend)
    _delete_network(network, backend, depends=depends)


def _delete_network(network, backend, depends=[]):
    depends = create_job_dependencies(depends)
    with pooled_rapi_client(backend) as client:
        return client.DeleteNetwork(network.backend_id, depends)


def disconnect_network(network, backend, group=None):
    log.debug("Disconnecting network %s to backend %s", network, backend)

    with pooled_rapi_client(backend) as client:
        groups = [group] if group is not None else client.GetGroups()
        job_ids = []
        for group in groups:
            job_id = client.DisconnectNetwork(network.backend_id, group)
            job_ids.append(job_id)
    return job_ids


def connect_to_network(vm, nic):
    network = nic.network
    backend = vm.backend
    bnet, depend_jobs = ensure_network_is_active(backend, network.id)

    depends = create_job_dependencies(depend_jobs)

    nic = {'name': nic.backend_uuid,
           'network': network.backend_id,
           'ip': nic.ipv4_address}

    log.debug("Adding NIC %s to VM %s", nic, vm)

    kwargs = {
        "instance": vm.backend_vm_id,
        "nics": [("add", "-1", nic)],
        "depends": depends,
    }
    if vm.backend.use_hotplug():
        kwargs["hotplug_if_possible"] = True
    if settings.TEST:
        kwargs["dry_run"] = True

    with pooled_rapi_client(vm) as client:
        return client.ModifyInstance(**kwargs)


def disconnect_from_network(vm, nic):
    log.debug("Removing NIC %s of VM %s", nic, vm)

    kwargs = {
        "instance": vm.backend_vm_id,
        "nics": [("remove", nic.backend_uuid, {})],
    }
    if vm.backend.use_hotplug():
        kwargs["hotplug_if_possible"] = True
    if settings.TEST:
        kwargs["dry_run"] = True

    with pooled_rapi_client(vm) as client:
        jobID = client.ModifyInstance(**kwargs)
        firewall_profile = nic.firewall_profile
        if firewall_profile and firewall_profile != "DISABLED":
            tag = _firewall_tags[firewall_profile] % nic.backend_uuid
            client.DeleteInstanceTags(vm.backend_vm_id, [tag],
                                      dry_run=settings.TEST)

        return jobID


def set_firewall_profile(vm, profile, nic):
    uuid = nic.backend_uuid
    try:
        tag = _firewall_tags[profile] % uuid
    except KeyError:
        raise ValueError("Unsopported Firewall Profile: %s" % profile)

    log.debug("Setting tag of VM %s, NIC %s, to %s", vm, nic, profile)

    with pooled_rapi_client(vm) as client:
        # Delete previous firewall tags
        old_tags = client.GetInstanceTags(vm.backend_vm_id)
        delete_tags = [(t % uuid) for t in _firewall_tags.values()
                       if (t % uuid) in old_tags]
        if delete_tags:
            client.DeleteInstanceTags(vm.backend_vm_id, delete_tags,
                                      dry_run=settings.TEST)

        if profile != "DISABLED":
            client.AddInstanceTags(vm.backend_vm_id, [tag],
                                   dry_run=settings.TEST)

        # XXX NOP ModifyInstance call to force process_net_status to run
        # on the dispatcher
        os_name = settings.GANETI_CREATEINSTANCE_KWARGS['os']
        client.ModifyInstance(vm.backend_vm_id,
                              os_name=os_name)
    return None


def attach_volume(vm, volume, depends=[]):
    log.debug("Attaching volume %s to vm %s", volume, vm)

    disk = {"size": int(volume.size) << 10,
            "name": volume.backend_volume_uuid}

    disk_provider = volume.volume_type.provider
    if disk_provider is not None:
        disk["provider"] = disk_provider

    if volume.origin is not None:
        disk["origin"] = volume.origin

    kwargs = {
        "instance": vm.backend_vm_id,
        "disks": [("add", "-1", disk)],
        "depends": depends,
    }
    if vm.backend.use_hotplug():
        kwargs["hotplug_if_possible"] = True
    if settings.TEST:
        kwargs["dry_run"] = True

    with pooled_rapi_client(vm) as client:
        return client.ModifyInstance(**kwargs)


def detach_volume(vm, volume, depends=[]):
    log.debug("Removing volume %s from vm %s", volume, vm)
    kwargs = {
        "instance": vm.backend_vm_id,
        "disks": [("remove", volume.backend_volume_uuid, {})],
        "depends": depends,
    }
    if vm.backend.use_hotplug():
        kwargs["hotplug_if_possible"] = True
    if settings.TEST:
        kwargs["dry_run"] = True

    with pooled_rapi_client(vm) as client:
        return client.ModifyInstance(**kwargs)


def snapshot_instance(vm, snapshot_name, snapshot_id):
    #volume = instance.volumes.all()[0]
    reason = json.dumps({"snapshot_id": snapshot_id})
    with pooled_rapi_client(vm) as client:
        return client.SnapshotInstance(instance=vm.backend_vm_id,
                                       snapshot_name=snapshot_name,
                                       reason=reason)


def get_instances(backend, bulk=True):
    with pooled_rapi_client(backend) as c:
        return c.GetInstances(bulk=bulk)


def get_nodes(backend, bulk=True):
    with pooled_rapi_client(backend) as c:
        return c.GetNodes(bulk=bulk)


def get_jobs(backend, bulk=True):
    with pooled_rapi_client(backend) as c:
        return c.GetJobs(bulk=bulk)


def get_physical_resources(backend):
    """ Get the physical resources of a backend.

    Get the resources of a backend as reported by the backend (not the db).

    """
    nodes = get_nodes(backend, bulk=True)
    attr = ['mfree', 'mtotal', 'dfree', 'dtotal', 'pinst_cnt', 'ctotal']
    res = {}
    for a in attr:
        res[a] = 0
    for n in nodes:
        # Filter out drained, offline and not vm_capable nodes since they will
        # not take part in the vm allocation process
        can_host_vms = n['vm_capable'] and not (n['drained'] or n['offline'])
        if can_host_vms and n['cnodes']:
            for a in attr:
                res[a] += int(n[a] or 0)
    return res


def update_backend_resources(backend, resources=None):
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
    with pooled_rapi_client(backend) as client:
        instances = client.GetInstances(bulk=True)
    mem = 0
    for i in instances:
        mem += i['oper_ram']
    return mem


def get_available_disk_templates(backend):
    """Get the list of available disk templates of a Ganeti backend.

    The list contains the disk templates that are enabled in the Ganeti backend
    and also included in ipolicy-disk-templates.

    """
    with pooled_rapi_client(backend) as c:
        info = c.GetInfo()
    ipolicy_disk_templates = info["ipolicy"]["disk-templates"]
    try:
        enabled_disk_templates = info["enabled_disk_templates"]
        return [dp for dp in enabled_disk_templates
                if dp in ipolicy_disk_templates]
    except KeyError:
        # Ganeti < 2.8 does not have 'enabled_disk_templates'
        return ipolicy_disk_templates


def update_backend_disk_templates(backend):
    disk_templates = get_available_disk_templates(backend)
    backend.disk_templates = disk_templates
    backend.save()


##
## Synchronized operations for reconciliation
##


def create_network_synced(network, backend):
    result = _create_network_synced(network, backend)
    if result[0] != rapi.JOB_STATUS_SUCCESS:
        return result
    result = connect_network_synced(network, backend)
    return result


def _create_network_synced(network, backend):
    with pooled_rapi_client(backend) as client:
        job = _create_network(network, backend)
        result = wait_for_job(client, job)
    return result


def connect_network_synced(network, backend):
    with pooled_rapi_client(backend) as client:
        for group in client.GetGroups():
            job = client.ConnectNetwork(network.backend_id, group,
                                        network.mode, network.link)
            result = wait_for_job(client, job)
            if result[0] != rapi.JOB_STATUS_SUCCESS:
                return result

    return result


def wait_for_job(client, jobid):
    result = client.WaitForJobChange(jobid, ['status', 'opresult'], None, None)
    status = result['job_info'][0]
    while status not in rapi.JOB_STATUS_FINALIZED:
        result = client.WaitForJobChange(jobid, ['status', 'opresult'],
                                         [result], None)
        status = result['job_info'][0]

    if status == rapi.JOB_STATUS_SUCCESS:
        return (status, None)
    else:
        error = result['job_info'][1]
        return (status, error)


def create_job_dependencies(job_ids=[], job_states=None):
    """Transform a list of job IDs to Ganeti 'depends' attribute."""
    if job_states is None:
        job_states = list(rapi.JOB_STATUS_FINALIZED)
    assert(type(job_states) == list)
    return [[job_id, job_states] for job_id in job_ids]
