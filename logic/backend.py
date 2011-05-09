#
# Business Logic for communication with the Ganeti backend
#
# Copyright 2010 Greek Research and Technology Network
#

from django.conf import settings
from synnefo.db.models import VirtualMachine
from synnefo.logic import utils
from synnefo.util.rapi import GanetiRapiClient


rapi = GanetiRapiClient(*settings.GANETI_CLUSTER_INFO)


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
    if status == 'success':
        utils.update_state(vm, VirtualMachine.OPER_STATE_FROM_OPCODE[opcode])
        # Set the deleted flag explicitly, to cater for admin-initiated removals
        if opcode == 'OP_INSTANCE_REMOVE':
            vm.deleted = True

    # Special case: if OP_INSTANCE_CREATE fails --> ERROR
    if status in ('canceled', 'error') and opcode == 'OP_INSTANCE_CREATE':
        utils.update_state(vm, 'ERROR')
    # Any other notification of failure leaves the operating state unchanged

    vm.save()


def process_net_status(vm, nics):
    """Process a net status notification from the backend

    Process an incoming message from the Ganeti backend,
    detailing the NIC configuration of a VM instance.

    Update the state of the VM in the DB accordingly.

    """

    # For the time being, we can only update the ipfour field,
    # based on the IPv4 address of the first NIC
    vm.ipfour = nics[0]['ip']
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

    # Update the relevant flags if the VM is being suspended or destroyed
    if action == "DESTROY":
        vm.deleted = True
    elif action == "SUSPEND":
        vm.suspended = True
    elif action == "START":
        vm.suspended = False
    vm.save()


def create_instance(vm, flavor, password):
    # FIXME: `password` must be passed to the Ganeti OS provider via CreateInstance()
    return rapi.CreateInstance(
        mode='create',
        name=vm.backend_id,
        disk_template='plain',
        disks=[{"size": 2000}],         #FIXME: Always ask for a 2GB disk for now
        nics=[{}],
        os='debootstrap+default',       #TODO: select OS from imageRef
        ip_check=False,
        name_check=False,
        pnode=rapi.GetNodes()[0],       #TODO: verify if this is necessary
        dry_run=settings.TEST,
        beparams=dict(auto_balance=True, vcpus=flavor.cpu, memory=flavor.ram))

def delete_instance(vm):
    start_action(vm, 'DESTROY')
    rapi.DeleteInstance(vm.backend_id)


def reboot_instance(vm, reboot_type):
    assert reboot_type in ('soft', 'hard')
    rapi.RebootInstance(vm.backend_id, reboot_type)


def startup_instance(vm):
    start_action(vm, 'START')
    rapi.StartupInstance(vm.backend_id)


def shutdown_instance(vm):
    start_action(vm, 'STOP')
    rapi.ShutdownInstance(vm.backend_id)


def get_instance_console(vm):
    return rapi.GetInstanceConsole(vm.backend_id)
