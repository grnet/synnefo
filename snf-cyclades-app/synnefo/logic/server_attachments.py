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

import logging

from snf_django.lib.api import faults
from django.conf import settings
from synnefo.logic import backend, commands

log = logging.getLogger(__name__)


def attach_volume(vm, volume):
    """Attach a volume to a server.

    The volume must be in 'AVAILABLE' status in order to be attached. Also,
    number of the volumes that are attached to the server must remain less
    than 'GANETI_MAX_DISKS_PER_INSTANCE' setting. This function will send
    the corresponding job to Ganeti backend and update the status of the
    volume to 'ATTACHING'.

    """
    # Check volume state
    if volume.status not in ["AVAILABLE", "CREATING"]:
        raise faults.BadRequest("Cannot attach volume while volume is in"
                                " '%s' status." % volume.status)

    # Check that disk templates are the same
    if volume.volume_type_id != vm.flavor.volume_type_id:
        msg = ("Volume and server must have the same volume type. Volume has"
               " volume type '%s' while server has '%s'"
               % (volume.volume_type_id, vm.flavor.volume_type_id))
        raise faults.BadRequest(msg)

    # Check maximum disk per instance hard limit
    vm_volumes_num = vm.volumes.filter(deleted=False).count()
    if vm_volumes_num == settings.GANETI_MAX_DISKS_PER_INSTANCE:
        raise faults.BadRequest("Maximum volumes per server limit reached")

    if volume.status == "CREATING":
        action_fields = {"disks": [("add", volume, {})]}
    else:
        action_fields = {}
    comm = commands.server_command("ATTACH_VOLUME",
                                   action_fields=action_fields)
    return comm(_attach_volume)(vm, volume)


def _attach_volume(vm, volume):
    """Attach a Volume to a VM and update the Volume's status."""
    jobid = backend.attach_volume(vm, volume)
    log.info("Attached volume '%s' to server '%s'. JobID: '%s'", volume.id,
             volume.machine_id, jobid)
    volume.backendjobid = jobid
    volume.machine = vm
    if volume.status == "AVAILALBE":
        volume.status = "ATTACHING"
    else:
        volume.status = "CREATING"
    volume.save()
    return jobid


def detach_volume(vm, volume):
    """Detach a Volume from a VM

    The volume must be in 'IN_USE' status in order to be detached. Also,
    the root volume of the instance (index=0) can not be detached. This
    function will send the corresponding job to Ganeti backend and update the
    status of the volume to 'DETACHING'.

    """

    _check_attachment(vm, volume)
    if volume.status not in ["IN_USE", "ERROR"]:
        raise faults.BadRequest("Cannot detach volume while volume is in"
                                " '%s' status." % volume.status)
    if volume.index == 0:
        raise faults.BadRequest("Cannot detach the root volume of a server")

    action_fields = {"disks": [("remove", volume, {})]}
    comm = commands.server_command("DETACH_VOLUME",
                                   action_fields=action_fields)
    return comm(_detach_volume)(vm, volume)


def _detach_volume(vm, volume):
    """Detach a Volume from a VM and update the Volume's status"""
    jobid = backend.detach_volume(vm, volume)
    log.info("Detached volume '%s' from server '%s'. JobID: '%s'", volume.id,
             volume.machine_id, jobid)
    volume.backendjobid = jobid
    if volume.delete_on_termination:
        volume.status = "DELETING"
    else:
        volume.status = "DETACHING"
    volume.save()
    return jobid


def _check_attachment(vm, volume):
    """Check that the Volume is attached to the VM"""
    if volume.machine_id != vm.id:
        raise faults.BadRequest("Volume '%s' is not attached to server '%s'"
                                % volume.id, vm.id)
