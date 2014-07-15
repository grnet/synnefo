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

from functools import wraps
from django.db import transaction

from django.conf import settings
from snf_django.lib.api import faults
from synnefo import quotas
from synnefo.db.models import VirtualMachine


log = logging.getLogger(__name__)


def validate_server_action(vm, action):
    if vm.deleted:
        raise faults.BadRequest("Server '%s' has been deleted." % vm.id)

    # Destroying a server should always be permitted
    if action == "DESTROY":
        return

    # Check that there is no pending action
    pending_action = vm.task
    if pending_action:
        if pending_action == "BUILD":
            raise faults.BuildInProgress("Server '%s' is being built." % vm.id)
        raise faults.BadRequest("Cannot perform '%s' action while there is a"
                                " pending '%s'." % (action, pending_action))

    # Reassigning is permitted in any state
    if action == "REASSIGN":
        return

    # Check if action can be performed to VM's operstate
    operstate = vm.operstate
    if operstate == "ERROR":
        raise faults.BadRequest("Cannot perform '%s' action while server is"
                                " in 'ERROR' state." % action)
    elif operstate == "BUILD" and action != "BUILD":
        raise faults.BuildInProgress("Server '%s' is being built." % vm.id)
    elif (action == "START" and operstate != "STOPPED") or\
         (action == "STOP" and operstate != "STARTED") or\
         (action == "RESIZE" and operstate != "STOPPED") or\
         (action in ["CONNECT", "DISCONNECT"]
          and operstate != "STOPPED"
          and not settings.GANETI_USE_HOTPLUG) or \
         (action in ["ATTACH_VOLUME", "DETACH_VOLUME"]
          and operstate != "STOPPED"
          and not settings.GANETI_USE_HOTPLUG):
        raise faults.BadRequest("Cannot perform '%s' action while server is"
                                " in '%s' state." % (action, operstate))
    return


def server_command(action, action_fields=None):
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
                                              action_fields=action_fields,
                                              commission_name=commission_name)
            vm.save()

            # XXX: Special case for server creation!
            if action == "BUILD":
                serial = vm.serial
                serial.pending = False
                serial.accept = True
                serial.save()
                # Perform a commit, because the VirtualMachine must be saved to
                # DB before the OP_INSTANCE_CREATE job in enqueued in Ganeti.
                # Otherwise, messages will arrive from snf-dispatcher about
                # this instance, before the VM is stored in DB.
                transaction.commit()
                # After committing the locks are released. Refetch the instance
                # to guarantee x-lock.
                vm = VirtualMachine.objects.select_for_update().get(id=vm.id)
                # XXX: Special case for server creation: we must accept the
                # commission because the VM has been stored in DB. Also, if
                # communication with Ganeti fails, the job will never reach
                # Ganeti, and the commission will never be resolved.
                quotas.accept_resource_serial(vm)

            # Send the job to Ganeti and get the associated jobID
            try:
                job_id = func(vm, *args, **kwargs)
            except Exception as e:
                if vm.serial is not None and action != "BUILD":
                    # Since the job never reached Ganeti, reject the commission
                    log.debug("Rejecting commission: '%s', could not perform"
                              " action '%s': %s" % (vm.serial,  action, e))
                    transaction.rollback()
                    quotas.reject_serial(vm.serial)
                    transaction.commit()
                raise

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
