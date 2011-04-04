#
# Utility functions
#
# Various functions
#
# Copyright 2010 Greek Research and Technology Network
#

from synnefo.db.models import VirtualMachine
from synnefo.logic import credits

import synnefo.settings as settings

def id_from_instance_name(name):
    """Returns VirtualMachine's Django id, given a ganeti machine name.

    Strips the ganeti prefix atm. Needs a better name!

    """
    if not str(name).startswith(settings.BACKEND_PREFIX_ID):
        raise VirtualMachine.InvalidBackendIdError(str(name))
    ns = str(name).lstrip(settings.BACKEND_PREFIX_ID)
    if not ns.isdigit():
        raise VirtualMachine.InvalidBackendIdError(str(name))

    return int(ns)


def get_rsapi_state(vm):
    """Returns the RSAPI state for a virtual machine"""
    try:
        r = VirtualMachine.RSAPI_STATE_FROM_OPER_STATE[vm.operstate]
    except KeyError:
        return "UNKNOWN"
    # A machine is DELETED if the deleted flag has been set
    if vm.deleted:
        return "DELETED"
    # A machine is in REBOOT if an OP_INSTANCE_REBOOT request is in progress
    if r == 'ACTIVE' and vm.backendopcode == 'OP_INSTANCE_REBOOT' and \
        vm.backendjobstatus in ('queued', 'waiting', 'running'):
        return "REBOOT"
    return r

def update_state(vm, new_operstate):
    """Wrapper around updates of the VirtualMachine.operstate field"""

    # Call charge() unconditionally before any change of
    # internal state.
    credits.charge(vm)
    vm.operstate = new_operstate
