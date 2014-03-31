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

    # Destroyin a server should always be permitted
    if action == "DESTROY":
        return

    # Check that there is no pending action
    pending_action = vm.task
    if pending_action:
        if pending_action == "BUILD":
            raise faults.BuildInProgress("Server '%s' is being build." % vm.id)
        raise faults.BadRequest("Cannot perform '%s' action while there is a"
                                " pending '%s'." % (action, pending_action))

    # Check if action can be performed to VM's operstate
    operstate = vm.operstate
    if operstate == "ERROR":
        raise faults.BadRequest("Cannot perform '%s' action while server is"
                                " in 'ERROR' state." % action)
    elif operstate == "BUILD" and action != "BUILD":
        raise faults.BuildInProgress("Server '%s' is being build." % vm.id)
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
                # Perform a commit, because the VirtualMachine must be saved to
                # DB before the OP_INSTANCE_CREATE job in enqueued in Ganeti.
                # Otherwise, messages will arrive from snf-dispatcher about
                # this instance, before the VM is stored in DB.
                transaction.commit()
                # After committing the locks are released. Refetch the instance
                # to guarantee x-lock.
                vm = VirtualMachine.objects.select_for_update().get(id=vm.id)

            # Send the job to Ganeti and get the associated jobID
            try:
                job_id = func(vm, *args, **kwargs)
            except Exception as e:
                if vm.serial is not None:
                    # Since the job never reached Ganeti, reject the commission
                    log.debug("Rejecting commission: '%s', could not perform"
                              " action '%s': %s" % (vm.serial,  action, e))
                    transaction.rollback()
                    quotas.reject_resource_serial(vm)
                    transaction.commit()
                raise

            if action == "BUILD" and vm.serial is not None:
                # XXX: Special case for server creation: we must accept the
                # commission because the VM has been stored in DB. Also, if
                # communication with Ganeti fails, the job will never reach
                # Ganeti, and the commission will never be resolved.
                quotas.accept_resource_serial(vm)

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
