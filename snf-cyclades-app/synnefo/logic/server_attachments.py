# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

import logging

from snf_django.lib.api import faults
from django.conf import settings
from synnefo.logic import backend, commands

log = logging.getLogger(__name__)


@commands.server_command("ATTACH_VOLUME")
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
    if volume.disk_template != vm.flavor.disk_template:
        msg = ("Volume and server must have the same disk template. Volume has"
               " disk template '%s' while server has '%s'"
               % (volume.disk_template, vm.flavor.disk_template))
        raise faults.BadRequest(msg)

    # Check maximum disk per instance hard limit
    if vm.volumes.filter(deleted=False).count() == settings.GANETI_MAX_DISKS_PER_INSTANCE:
        raise faults.BadRequest("Maximum volumes per server limit reached")

    jobid = backend.attach_volume(vm, volume)

    log.info("Attached volume '%s' to server '%s'. JobID: '%s'", volume.id,
             volume.machine_id, jobid)

    volume.backendjobid = jobid
    volume.machine = vm
    volume.status = "ATTACHING"
    volume.save()
    return jobid


@commands.server_command("DETACH_VOLUME")
def detach_volume(vm, volume):
    """Detach a volume to a server.

    The volume must be in 'IN_USE' status in order to be detached. Also,
    the root volume of the instance (index=0) can not be detached. This
    function will send the corresponding job to Ganeti backend and update the
    status of the volume to 'DETACHING'.

    """

    _check_attachment(vm, volume)
    if volume.status != "IN_USE":
        #TODO: Maybe allow other statuses as well ?
        raise faults.BadRequest("Cannot detach volume while volume is in"
                                " '%s' status." % volume.status)
    if volume.index == 0:
        raise faults.BadRequest("Cannot detach the root volume of a server")
    jobid = backend.detach_volume(vm, volume)
    log.info("Detached volume '%s' from server '%s'. JobID: '%s'", volume.id,
             volume.machine_id, jobid)
    volume.backendjobid = jobid
    volume.status = "DETACHING"
    volume.save()
    return jobid


def _check_attachment(vm, volume):
    """Check that volume is attached to vm."""
    if volume.machine_id != vm.id:
        raise faults.BadRequest("Volume '%s' is not attached to server '%s'"
                                % volume.id, vm.id)
