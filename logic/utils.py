#
# Various utility functions
#
# Copyright 2010 Greek Research and Technology Network
#
from django.conf import settings

from db.models import VirtualMachine

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
        r = VirtualMachine.RSAPI_STATE_FROM_OPER_STATE[vm._operstate]
    except KeyError:
        return "UNKNOWN"
    # A machine is in REBOOT if an OP_INSTANCE_REBOOT request is in progress
    if r == 'ACTIVE' and vm._backendopcode == 'OP_INSTANCE_REBOOT' and \
        vm._backendjobstatus in ('queued', 'waiting', 'running'):
        return "REBOOT"
    return r


def calculate_cost(start_date, end_date, cost):
    """Calculate the total cost for the specified duration"""
    td = end_date - start_date
    sec = float(td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / float(10**6)
    total_hours = float(sec) / float(60.0*60.0)
    total_cost = float(cost)*total_hours

    return round(total_cost)
