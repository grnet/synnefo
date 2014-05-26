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

# Utility functions

from synnefo.db.models import VirtualMachine, Network
from snf_django.lib.api import faults
from django.conf import settings
from copy import deepcopy
from django.utils.encoding import smart_unicode


def id_from_instance_name(name):
    """Returns VirtualMachine's Django id, given a ganeti machine name.

    Strips the ganeti prefix atm. Needs a better name!

    """
    sname = smart_unicode(name)
    if not sname.startswith(settings.BACKEND_PREFIX_ID):
        raise VirtualMachine.InvalidBackendIdError(sname)
    ns = sname.replace(settings.BACKEND_PREFIX_ID, "", 1)
    if not ns.isdigit():
        raise VirtualMachine.InvalidBackendIdError(sname)

    return int(ns)


def id_to_instance_name(id):
    return "%s%s" % (settings.BACKEND_PREFIX_ID, smart_unicode(id))


def id_from_network_name(name):
    """Returns Network's Django id, given a ganeti network name.

    Strips the ganeti prefix atm. Needs a better name!

    """
    name = smart_unicode(name)
    if not name.startswith(settings.BACKEND_PREFIX_ID):
        raise Network.InvalidBackendIdError(name)
    ns = name.replace(settings.BACKEND_PREFIX_ID + 'net-', "", 1)
    if not ns.isdigit():
        raise Network.InvalidBackendIdError(smart_unicode(name))

    return int(ns)


def id_to_network_name(id):
    return "%snet-%s" % (settings.BACKEND_PREFIX_ID, smart_unicode(id))


def id_from_nic_name(name):
    """Returns NIC's Django id, given a Ganeti's NIC name.

    """
    name = smart_unicode(name)
    if not name.startswith(settings.BACKEND_PREFIX_ID):
        raise ValueError("Invalid NIC name: %s" % name)
    ns = name.replace(settings.BACKEND_PREFIX_ID + 'nic-', "", 1)
    if not ns.isdigit():
        raise ValueError("Invalid NIC name: %s" % name)

    return int(ns)


def id_from_disk_name(name):
    """Returns Disk Django id, given a Ganeti's Disk name.

    """
    if not str(name).startswith(settings.BACKEND_PREFIX_ID):
        raise ValueError("Invalid Disk name: %s" % name)
    ns = str(name).replace(settings.BACKEND_PREFIX_ID + 'vol-', "", 1)
    if not ns.isdigit():
        raise ValueError("Invalid Disk name: %s" % name)

    return int(ns)


def id_to_disk_name(id):
    return "%svol-%s" % (settings.BACKEND_PREFIX_ID, str(id))


def get_rsapi_state(vm):
    """Returns the API state for a virtual machine

    The API state for an instance of VirtualMachine is derived as follows:

    * If the deleted flag has been set, it is "DELETED".
    * Otherwise, it is a mapping of the last state reported by Ganeti
      (vm.operstate) through the RSAPI_STATE_FROM_OPER_STATE dictionary.

      The last state reported by Ganeti is set whenever Ganeti reports
      successful completion of an operation. If Ganeti says an
      OP_INSTANCE_STARTUP operation succeeded, vm.operstate is set to
      "STARTED".

    * To support any transitional states defined by the API (only REBOOT for
    the time being) this mapping is amended with information reported by Ganeti
    regarding any outstanding operation. If an OP_INSTANCE_STARTUP had
    succeeded previously and an OP_INSTANCE_REBOOT has been reported as in
    progress, the API state is "REBOOT".

    """
    try:
        r = VirtualMachine.RSAPI_STATE_FROM_OPER_STATE[vm.operstate]
    except KeyError:
        return "UNKNOWN"
    # A machine is DELETED if the deleted flag has been set
    if vm.deleted:
        return "DELETED"
    # A machine is in REBOOT if an OP_INSTANCE_REBOOT request is in progress
    in_reboot = (r == "ACTIVE") and\
                (vm.backendopcode == "OP_INSTANCE_REBOOT") and\
                (vm.backendjobstatus in ("queued", "waiting", "running"))
    if in_reboot:
        return "REBOOT"
    in_resize = (r == "STOPPED") and\
                (vm.backendopcode == "OP_INSTANCE_MODIFY") and\
                (vm.task == "RESIZE") and \
                (vm.backendjobstatus in ("queued", "waiting", "running"))
    if in_resize:
        return "RESIZE"
    return r


TASK_STATE_FROM_ACTION = {
    "BUILD": "BUILDING",
    "START": "STARTING",
    "STOP": "STOPPING",
    "REBOOT": "REBOOTING",
    "DESTROY": "DESTROYING",
    "RESIZE": "RESIZING",
    "CONNECT": "CONNECTING",
    "DISCONNECT": "DISCONNECTING",
    "ATTACH_VOLUME": "ATTACHING_VOLUME",
    "DETACH_VOLUME": "DETACHING_VOLUME"}


def get_task_state(vm):
    if vm.task is None:
        return ""
    try:
        return TASK_STATE_FROM_ACTION[vm.task]
    except KeyError:
        return "UNKNOWN"


OPCODE_TO_ACTION = {
    "OP_INSTANCE_CREATE": "BUILD",
    "OP_INSTANCE_STARTUP": "START",
    "OP_INSTANCE_SHUTDOWN": "STOP",
    "OP_INSTANCE_REBOOT": "REBOOT",
    "OP_INSTANCE_REMOVE": "DESTROY"}


def get_action_from_opcode(opcode, job_fields):
    if opcode == "OP_INSTANCE_SET_PARAMS":
        nics = job_fields.get("nics")
        disks = job_fields.get("disks")
        beparams = job_fields.get("beparams")
        if nics:
            try:
                nic_action = nics[0][0]
                if nic_action == "add":
                    return "CONNECT"
                elif nic_action == "remove":
                    return "DISCONNECT"
                else:
                    return None
            except:
                return None
        if disks:
            try:
                disk_action = disks[0][0]
                if disk_action == "add":
                    return "ATTACH_VOLUME"
                elif disk_action == "remove":
                    return "DETACH_VOLUME"
                elif disk_action == "modify":
                    return "MODIFY_VOLUME"
                else:
                    return None
            except:
                return None
        elif beparams:
            return "RESIZE"
        else:
            return None
    else:
        return OPCODE_TO_ACTION.get(opcode, None)


def hide_pass(kw):
    if 'osparams' in kw and 'img_passwd' in kw['osparams']:
        kw1 = deepcopy(kw)
        kw1['osparams']['img_passwd'] = 'x' * 8
        return kw1
    else:
        return kw


def check_name_length(name, max_length, message):
    """Check if a string is within acceptable value length"""
    name = smart_unicode(name, encoding="utf-8")
    if len(name) > max_length:
        raise faults.BadRequest(message)
