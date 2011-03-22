
from db.models import VirtualMachine

def process_backend_msg(vm, jobid, opcode, status, logmsg):
    """Process a job progress notification from the backend.

    Process an incoming message from the backend (currently Ganeti).
    Job notifications with a terminating status (sucess, error, or canceled),
    also update the operating state of the VM.

    """
    if (opcode not in [x[0] for x in VirtualMachine.BACKEND_OPCODES] or
       status not in [x[0] for x in VirtualMachine.BACKEND_STATUSES]):
        raise VirtualMachine.InvalidBackendMsgError(opcode, status)

    vm._backendjobid = jobid
    vm._backendjobstatus = status
    vm._backendopcode = opcode
    vm._backendlogmsg = logmsg

    # Notifications of success change the operating state
    if status == 'success':
        vm._update_state(VirtualMachine.OPER_STATE_FROM_OPCODE[opcode])
    # Special cases OP_INSTANCE_CREATE fails --> ERROR
    if status in ('canceled', 'error') and opcode == 'OP_INSTANCE_CREATE':
        vm._update_state('ERROR')
    # Any other notification of failure leaves the operating state unchanged

    vm.save()
