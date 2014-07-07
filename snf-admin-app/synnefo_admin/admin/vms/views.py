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
import re
from collections import OrderedDict
import time

from operator import or_

from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils.html import escape

from synnefo.db.models import (VirtualMachine, Network, IPAddressLog,
                               IPAddress)
from astakos.im.models import AstakosUser, ProjectMembership, Project
from astakos.im.user_utils import send_plain as send_email

from synnefo.logic import servers as servers_backend
from synnefo.logic.commands import validate_server_action
from synnefo.management.common import wait_server_task


import django_filters

from synnefo_admin.admin.actions import (has_permission_or_403,
                                         get_allowed_actions,
                                         get_permitted_actions,)
from synnefo_admin.admin.utils import get_actions, render_email
from synnefo_admin.admin.users.utils import get_user
from synnefo_admin.admin.tables import AdminJSONView

from .utils import get_flavor_info, get_vm, get_user_details_href
from .filters import VMFilterSet
from .actions import cached_actions

templates = {
    'list': 'admin/vm_list.html',
    'details': 'admin/vm_details.html',
}


class VMJSONView(AdminJSONView):
    model = VirtualMachine
    fields = ('pk', 'name', 'operstate', 'suspended',)
    filters = VMFilterSet

    def get_extra_data(self, qs):
        # FIXME: The `contact_name`, `contact_email` fields will cripple our db
        if self.form.cleaned_data['iDisplayLength'] < 0:
            qs = qs.only('pk', 'name', 'operstate', 'suspended', 'id',
                         'deleted', 'task', 'userid')
        return [self.get_extra_data_row(row) for row in qs]

    def get_extra_data_row(self, inst):
        if self.dt_data['iDisplayLength'] < 0:
            extra_dict = {}
        else:
            extra_dict = OrderedDict()

        extra_dict['allowed_actions'] = {
            'display_name': "",
            'value': get_allowed_actions(cached_actions, inst),
            'visible': False,
        }
        extra_dict['id'] = {
            'display_name': "ID",
            'value': inst.pk,
            'visible': False,
        }
        extra_dict['item_name'] = {
            'display_name': "Name",
            'value': escape(inst.name),
            'visible': False,
        }
        extra_dict['details_url'] = {
            'display_name': "Details",
            'value': reverse('admin-details', args=['vm', inst.pk]),
            'visible': True,
        }
        extra_dict['contact_id'] = {
            'display_name': "Contact ID",
            'value': inst.userid,
            'visible': False,
        }
        extra_dict['contact_email'] = {
            'display_name': "Contact email",
            'value': escape(AstakosUser.objects.get(uuid=inst.userid).email),
            'visible': False,
        }
        extra_dict['contact_name'] = {
            'display_name': "Contact name",
            'value': escape(AstakosUser.objects.get(uuid=inst.userid).realname),
            'visible': False,
        }

        if self.form.cleaned_data['iDisplayLength'] < 0:
            extra_dict['minimal'] = {
                'display_name': "No summary available",
                'value': "Have you per chance pressed 'Select All'?",
                'visible': True,
            }
        else:
            extra_dict.update(self.add_verbose_data(inst))

        return extra_dict

    def add_verbose_data(self, inst):
        extra_dict = OrderedDict()
        extra_dict['user_info'] = {
            'display_name': "User",
            'value': get_user_details_href(inst),
            'visible': True,
        }
        extra_dict['image_id'] = {
            'display_name': "Image ID",
            'value': inst.imageid,
            'visible': True,
        }
        extra_dict['flavor_info'] = {
            'display_name': "Flavor info",
            'value': get_flavor_info(inst),
            'visible': True,
        }
        extra_dict['created'] = {
            'display_name': "Created",
            'value': inst.created.strftime("%Y-%m-%d %H:%M"),
            'visible': True,
        }
        extra_dict['updated'] = {
            'display_name': "Updated",
            'value': inst.updated.strftime("%Y-%m-%d %H:%M"),
            'visible': True,
        }

        return extra_dict


@has_permission_or_403(cached_actions)
def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    if op == "contact":
        user = get_user(id)
    else:
        vm = get_vm(id)
    actions = get_permitted_actions(cached_actions, request.user)

    if op == 'reboot':
        actions[op].f(vm, "SOFT")
    elif op == 'contact':
        subject, body = render_email(request.POST, user)
        actions[op].f(user, subject, template_name=None, text=body)
    else:
        actions[op].f(vm)


@has_permission_or_403(cached_actions)
def wait_action(request, op, id):
    """Wait for the requested action to end."""
    if op == "contact" or op == "suspend" or op == "unsuspend":
        return

    terminal_state = ["ERROR"]
    if op == "start" or op == "reboot":
        terminal_state.append("STARTED")
    elif op == "shutdown":
        terminal_state.append("STOPPED")
    elif op == "destroy":
        terminal_state.append("DESTROYED")

    while True:
        vm = get_vm(id)
        if vm.operstate in terminal_state:
            break
        time.sleep(1)

    return


def catalog(request):
    """List view for Cyclades VMs."""
    logging.info("Filters are %s", VMFilterSet().filters)
    context = {}
    context['action_dict'] = get_permitted_actions(cached_actions, request.user)
    context['filter_dict'] = VMFilterSet().filters.itervalues()
    context['columns'] = ["ID", "Name", "State", "Suspended", ""]
    context['item_type'] = 'vm'

    return context


def details(request, query):
    """Details view for Astakos users."""
    vm = get_vm(query)
    user_list = AstakosUser.objects.filter(uuid=vm.userid)
    project_list = Project.objects.filter(uuid=vm.project)
    volume_list = vm.volumes.all()
    network_list = Network.objects.filter(machines__pk=vm.pk)
    nic_list = vm.nics.all()
    ip_list = [nic.ips.all() for nic in nic_list]
    ip_list = reduce(or_, ip_list) if ip_list else ip_list

    ip_log_list = IPAddressLog.objects.filter(server_id=vm.pk)\
        .order_by("allocated_at")

    for ipaddr in ip_log_list:
        ipaddr.vm = vm
        ipaddr.network = Network.objects.get(id=ipaddr.network_id)
        ipaddr.user = AstakosUser.objects.get(uuid=ipaddr.vm.userid)

    context = {
        'main_item': vm,
        'main_type': 'vm',
        'action_dict': get_permitted_actions(cached_actions, request.user),
        'associations_list': [
            (user_list, 'user', get_actions("user", request.user)),
            (project_list, 'project', get_actions("project", request.user)),
            (volume_list, 'volume', get_actions("volume", request.user)),
            (network_list, 'network', get_actions("network", request.user)),
            (nic_list, 'nic', None),
            (ip_list, 'ip', get_actions("ip", request.user)),
            (ip_log_list, 'ip_log', None),
        ]
    }

    return context
