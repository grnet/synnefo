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

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse

from synnefo.db.models import (Network, VirtualMachine, NetworkInterface,
                               IPAddress, IPAddressLog)
from synnefo.logic.networks import validate_network_action
from synnefo.logic import networks
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView
import django_filters

from synnefo_admin.admin.actions import (has_permission_or_403,
                                         get_allowed_actions,
                                         get_permitted_actions,)
from synnefo_admin.admin.utils import get_actions, render_email
from synnefo_admin.admin.users.utils import get_user

from .filters import NetworkFilterSet
from .actions import cached_actions
from .utils import (get_contact_name, get_contact_email, get_network,
                    get_user_details_href)


templates = {
    'list': 'admin/network_list.html',
    'details': 'admin/network_details.html',
}


class NetworkJSONView(DatatablesView):
    model = Network
    fields = ('pk', 'name', 'state', 'public', 'drained',)
    filters = NetworkFilterSet

    def format_data_row(self, row):
        if not row[1]:
            row = list(row)
            row[1] = "(not set)"
        return row

    def get_extra_data(self, qs):
        # FIXME: The `contact_name`, `contact_email` fields will cripple our db
        if self.form.cleaned_data['iDisplayLength'] < 0:
            qs = qs.only('pk', 'name', 'state', 'public', 'drained', 'userid',
                         'deleted')
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
            'value': inst.name,
            'visible': False,
        }
        extra_dict['details_url'] = {
            'display_name': "Details",
            'value': reverse('admin-details', args=['network', inst.pk]),
            'visible': True,
        }
        extra_dict['contact_id'] = {
            'display_name': "Contact ID",
            'value': inst.userid,
            'visible': False,
        }
        extra_dict['contact_email'] = {
            'display_name': "Contact email",
            'value': get_contact_email(inst),
            'visible': False,
        }
        extra_dict['contact_name'] = {
            'display_name': "Contact name",
            'value': get_contact_name(inst),
            'visible': False,
        }

        extra_dict['user_info'] = {
            'display_name': "User",
            'value': get_user_details_href(inst),
            'visible': True,
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
        extra_dict['public'] = {
            'display_name': "Public",
            'value': inst.public,
            'visible': True,
        }
        extra_dict['updated'] = {
            'display_name': "Update time",
            'value': inst.updated.strftime("%Y-%m-%d %H:%M"),
            'visible': True,
        }

        return extra_dict


@has_permission_or_403(cached_actions)
def do_action(request, op, id):
    """Apply the requested action on the specified network."""
    if op == "contact":
        user = get_user(id)
    else:
        network = Network.objects.get(pk=id)
    actions = get_permitted_actions(cached_actions, request.user)

    if op == 'contact':
        subject, body = render_email(request.POST, user)
        actions[op].f(user, subject, template_name=None, text=body)
    else:
        actions[op].f(network)


def catalog(request):
    """List view for Cyclades networks."""
    context = {}
    context['action_dict'] = get_permitted_actions(cached_actions, request.user)
    context['filter_dict'] = NetworkFilterSet().filters.itervalues()
    context['columns'] = ["ID", "Name", "Status", "Public",
                          "Drained", ""]
    context['item_type'] = 'network'

    return context


def details(request, query):
    """Details view for Astakos users."""
    error = request.GET.get('error', None)

    network = get_network(query)
    vm_list = network.machines.all()
    nic_list = NetworkInterface.objects.filter(network=network)
    ip_list = IPAddress.objects.filter(network=network)
    user_list = AstakosUser.objects.filter(uuid=network.userid)
    project_list = Project.objects.filter(uuid=network.project)

    ip_log_list = IPAddressLog.objects.filter(network_id=network.pk)\
        .order_by("allocated_at")

    for ipaddr in ip_log_list:
        ipaddr.ip = IPAddress.objects.get(address=ipaddr.address)
        ipaddr.vm = VirtualMachine.objects.get(id=ipaddr.server_id)
        ipaddr.network = network
        ipaddr.user = AstakosUser.objects.get(uuid=ipaddr.vm.userid)

    context = {
        'main_item': network,
        'main_type': 'network',
        'action_dict': get_permitted_actions(cached_actions, request.user),
        'associations_list': [
            (vm_list, 'vm', get_actions("vm", request.user)),
            (nic_list, 'nic', None),
            (ip_list, 'ip', get_actions("ip", request.user)),
            (user_list, 'user', get_actions("user", request.user)),
            (project_list, 'project', get_actions("project", request.user)),
            (ip_log_list, 'ip_log', None),
        ]
    }

    return context
