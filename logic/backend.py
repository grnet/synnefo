
from db.models import VirtualMachine
import utils

def process_backend_msg(vm, jobid, opcode, status, logmsg):
    """Process a job progress notification from the backend.

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
        utils.update_state(VirtualMachine.OPER_STATE_FROM_OPCODE[opcode])
    # Special cases OP_INSTANCE_CREATE fails --> ERROR
    if status in ('canceled', 'error') and opcode == 'OP_INSTANCE_CREATE':
        utils.update_state('ERROR')
    # Any other notification of failure leaves the operating state unchanged

    vm.save()

def start_action(vm, action):
    """Update the state of a VM when a new action is initiated."""
    if not action in [x[0] for x in VirtualMachine.ACTIONS]:
        raise VirtualMachine.InvalidActionError(action)

    # No actions to deleted and no actions beside destroy to suspended VMs
    if vm.deleted:
        raise VirtualMachine.InvalidActionError(action)

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
