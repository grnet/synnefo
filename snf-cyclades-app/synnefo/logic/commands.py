# Copyright (C) 2010-2017 GRNET S.A.
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

from synnefo.db import models

from django.conf import settings
from snf_django.lib.api import faults
from synnefo import quotas
from synnefo.api import util


log = logging.getLogger(__name__)


def validate_server_action(vm, action):
    if vm.deleted:
        raise faults.BadRequest("Server '%s' has been deleted." % vm.id)

    if action == "SUSPEND":
        if vm.suspended:
            raise faults.BadRequest("Server already suspended.")
        return

    if action == "UNSUSPEND":
        if not vm.suspended:
            raise faults.BadRequest("Server already unsuspended.")
        return

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
         (action in ["ATTACH_VOLUME", "DETACH_VOLUME", "DELETE_VOLUME"]
          and operstate != "STOPPED"
          and not settings.GANETI_USE_HOTPLUG):
        raise faults.BadRequest("Cannot perform '%s' action while server is"
                                " in '%s' state." % (action, operstate))
    return


class ServerCommand(object):
    """Handle execution of a server action.

    Helper manager to validate a server action and handle quota commission.

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
    """

    def __init__(self, action, vm, credentials=None, atomic_context=None,
                 action_fields=None, for_user=None):
        if not isinstance(vm, models.VirtualMachine):
            vm = util.get_vm(vm, credentials,
                             for_update=True, non_deleted=True,
                             non_suspended=not credentials.is_admin)
        self.vm = vm
        user_id = for_user
        if user_id is None:
            user_id = vm.userid

        if action == "BUILD":
            raise AssertionError(
                "decorator does not support action 'BUILD'")

        validate_server_action(vm, action)
        vm.action = action

        commission_name = "client: api, resource: %s" % vm
        serial = quotas.handle_resource_commission(
            vm, action=action,
            action_fields=action_fields,
            commission_name=commission_name,
            for_user=user_id)
        if serial is not None:
            quotas.set_serial(atomic_context, serial)

    def __enter__(self):
        return self.vm

    def __exit__(self, type, value, traceback):
        pass
