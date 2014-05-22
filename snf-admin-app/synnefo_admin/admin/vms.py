# Copyright 2014 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import logging
import re
from collections import OrderedDict

from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse

from actions import AdminAction, nop

from synnefo.db.models import VirtualMachine, Network, IPAddressLog
from astakos.im.models import AstakosUser, ProjectMembership, Project
from astakos.im.functions import send_plain as send_email

from synnefo.logic import servers as servers_backend

from eztables.views import DatatablesView

templates = {
    'list': 'admin/vm_list.html',
    'details': 'admin/vm_details.html',
}


def get_allowed_actions(vm):
    """Get a list of actions that can apply to a user."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(vm):
            allowed_actions.append(key)

    return allowed_actions


def get_flavor_info(vm):
    return ('CPU: ' + str(vm.flavor.cpu) + ', RAM: ' + str(vm.flavor.ram) +
            ', Disk size: ' + str(vm.flavor.disk) + ', Disk template:' +
            str(vm.flavor.volume_type.disk_template))


class VMJSONView(DatatablesView):
    model = VirtualMachine
    fields = ('pk', 'pk', 'name', 'operstate',)

    extra = True

    def get_extra_data_row(self, inst):
        extra_dict = {
            'allowed_actions': {
                'display_name': "",
                'value': get_allowed_actions(inst),
                'visible': False,
            }, 'id': {
                'display_name': "ID",
                'value': inst.pk,
                'visible': False,
            }, 'item_name': {
                'display_name': "Name",
                'value': inst.name,
                'visible': False,
            }, 'details_url': {
                'display_name': "Details",
                'value': reverse('admin-details', args=['vm', inst.pk]),
                'visible': True,
            }, 'contact_id': {
                'display_name': "Contact ID",
                'value': inst.userid,
                'visible': False,
            }, 'contact_mail': {
                'display_name': "Contact mail",
                'value': AstakosUser.objects.get(uuid=inst.userid).email,
                'visible': True,
            }, 'contact_name': {
                'display_name': "Contact name",
                'value': AstakosUser.objects.get(uuid=inst.userid).realname,
                'visible': True,
            }, 'user_id': {
                'display_name': "User ID",
                'value': inst.userid,
                'visible': True,
            }, 'image_id': {
                'display_name': "Image ID",
                'value': inst.imageid,
                'visible': True,
            }, 'flavor_info': {
                'display_name': "Flavor info",
                'value': get_flavor_info(inst),
                'visible': True,
            }, 'created': {
                'display_name': "Created",
                'value': inst.created,
                'visible': True,
            }, 'updated': {
                'display_name': "Updated",
                'value': inst.updated,
                'visible': True,
            }, 'suspended': {
                'display_name': "Suspended",
                'value': inst.suspended,
                'visible': True,
            }
        }

        return extra_dict


class VMAction(AdminAction):

    """Class for actions on VMs. Derived from AdminAction.

    Pre-determined Attributes:
        target:        vm
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='vm', f=f, **kwargs)


def vm_suspend(vm):
    """Suspend a VM."""
    vm.suspended = True
    vm.save()


def vm_suspend_release(vm):
    """Release previous VM suspension."""
    vm.suspended = False
    vm.save()


def generate_actions():
    """Create a list of actions on users.

    The actions are: start/shutdown, restart, destroy,
                     suspend/release, reassign, contact
    """
    actions = OrderedDict()

    actions['start'] = VMAction(name='Start', f=servers_backend.start,
                                karma='good', reversible=True)

    actions['shutdown'] = VMAction(name='Shutdown', f=servers_backend.stop,
                                   karma='bad', reversible=True)

    actions['restart'] = VMAction(name='Reboot', f=servers_backend.reboot,
                                  karma='bad', reversible=True)

    actions['destroy'] = VMAction(name='Destroy', f=servers_backend.destroy,
                                  karma='bad', reversible=False)

    actions['suspend'] = VMAction(name='Suspend', f=vm_suspend,
                                  karma='bad', reversible=True)

    actions['release'] = VMAction(name='Release suspension',
                                  f=vm_suspend_release,
                                  karma='good', reversible=True)

    actions['reassign'] = VMAction(name='Reassign', f=nop,
                                   karma='neutral', reversible=True)

    actions['contact'] = VMAction(name='Send e-mail', f=send_email)

    return actions


def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    vm = VirtualMachine.objects.get(pk=id)
    actions = generate_actions()
    logging.info("Op: %s, vm: %s, function", op, vm.pk, actions[op].f)

    if op == 'restart':
        actions[op].f(vm, "SOFT")
    elif op == 'contact':
        user = AstakosUser.objects.get(uuid=vm.userid)
        actions[op].f(user, request.POST['text'])
    else:
        actions[op].f(vm)


def catalog(request):
    """List view for Cyclades VMs."""
    context = {}
    context['action_dict'] = generate_actions()
    context['columns'] = ["Column 1", "ID", "Name", "State", "Details",
                          "Summary"]
    context['item_type'] = 'vm'

    return context


def details(request, query):
    """Details view for Astakos users."""
    try:
        id = query.translate(None, 'vm-')
    except Exception:
        id = query

    vm = VirtualMachine.objects.get(pk=int(id))
    users = [AstakosUser.objects.get(uuid=vm.userid)]
    projects = [Project.objects.get(uuid=vm.project)]
    networks = vm.nics.all()

    context = {
        'main_item': vm,
        'main_type': 'vm',
        'associations_list': [
            (users, 'user'),
            (projects, 'project'),
            (networks, 'network'),
        ]
    }

    return context
