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
                               IPAddress)
from synnefo.logic.networks import validate_network_action
from synnefo.logic import networks
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView
import django_filters

from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from synnefo_admin.admin.utils import filter_owner_name
from synnefo_admin.admin.users.actions import get_permitted_actions as \
    get_user_actions
from synnefo_admin.admin.vms.actions import get_permitted_actions as \
    get_vm_actions
from synnefo_admin.admin.volumes.actions import get_permitted_actions as \
    get_volume_actions
from synnefo_admin.admin.ips.actions import get_permitted_actions as \
    get_ip_actions
from synnefo_admin.admin.projects.actions import get_permitted_actions as \
    get_project_actions

from .filters import NetworkFilterSet
from .actions import (generate_actions, get_allowed_actions,
                      get_permitted_actions)
from .utils import get_contact_name, get_contact_mail, get_network

templates = {
    'list': 'admin/network_list.html',
    'details': 'admin/network_details.html',
}


class NetworkJSONView(DatatablesView):
    model = Network
    fields = ('pk', 'name', 'state', 'public', 'drained',)

    extra = True
    filters = NetworkFilterSet

    def format_data_row(self, row):
        if not row[1]:
            row[1] = "-"
        return row

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
                'value': reverse('admin-details', args=['network', inst.id]),
                'visible': True,
            }, 'contact_id': {
                'display_name': "Contact ID",
                'value': inst.userid,
                'visible': False,
            }, 'contact_mail': {
                'display_name': "Contact mail",
                'value': get_contact_mail(inst),
                'visible': False,
            }, 'contact_name': {
                'display_name': "Contact name",
                'value': get_contact_name(inst),
                'visible': False,
            }, 'public': {
                'display_name': "Public",
                'value': inst.public,
                'visible': True,
            }, 'updated': {
                'display_name': "Update time",
                'value': inst.updated,
                'visible': True,
            }
        }

        return extra_dict


@has_permission_or_403(generate_actions())
def do_action(request, op, id):
    """Apply the requested action on the specified network."""
    network = Network.objects.get(pk=id)
    actions = get_permitted_actions(request.user)

    if op == 'contact':
        actions[op].f(network, request.POST['text'])
    else:
        actions[op].f(network)


def catalog(request):
    """List view for Cyclades networks."""
    context = {}
    context['action_dict'] = get_permitted_actions(request.user)
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

    context = {
        'main_item': network,
        'main_type': 'network',
        'action_dict': get_permitted_actions(request.user),
        'associations_list': [
            (vm_list, 'vm', get_vm_actions(request.user)),
            (nic_list, 'nic', None),
            (ip_list, 'ip', get_ip_actions(request.user)),
            (user_list, 'user', get_user_actions(request.user)),
            (project_list, 'project', get_project_actions(request.user)),
        ]
    }

    return context
