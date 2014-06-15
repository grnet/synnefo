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

from synnefo.db.models import IPAddress
from synnefo.logic import ips
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView
import django_filters

#import synnefo_admin.admin.vms as vm_views
from synnefo_admin.admin.utils import filter_owner_name
from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from .utils import get_contact_mail, get_contact_name
from .actions import (generate_actions, get_allowed_actions,
                      get_permitted_actions)
from .filters import IPFilterSet


templates = {
    'list': 'admin/ip_list.html',
    'details': 'admin/ip_details.html',
}


class IPJSONView(DatatablesView):
    model = IPAddress
    fields = ('pk', 'address', 'floating_ip', 'created', 'userid',)

    extra = True
    filters = IPFilterSet

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
                'value': inst.address,
                'visible': False,
            }, 'details_url': {
                'display_name': "Details",
                'value': reverse('admin-details', args=['ip', inst.pk]),
                'visible': True,
            }, 'contact_id': {
                'display_name': "Contact ID",
                'value': inst.userid,
                'visible': False,
            }, 'contact_mail': {
                'display_name': "Contact mail",
                'value': get_contact_mail(inst),
                'visible': True,
            }, 'contact_name': {
                'display_name': "Contact name",
                'value': get_contact_name(inst),
                'visible': True,
            }, 'updated': {
                'display_name': "Update date",
                'value': inst.updated,
                'visible': True,
            }, 'in_use': {
                'display_name': "Currently in Use",
                'value': inst.in_use(),
                'visible': True,
            }, 'network_info': {
                'display_name': "Network info",
                'value': ('ID: ' + str(inst.network.id) + ', Name: ' +
                          str(inst.network.id)),
                'visible': True,
            }
        }

        return extra_dict


@has_permission_or_403(generate_actions())
def do_action(request, op, id):
    """Apply the requested action on the specified ip."""
    ip = IPAddress.objects.get(id=id)
    actions = get_permitted_actions(request.user)

    if op == 'contact':
        actions[op].f(ip, request.POST['text'])
    else:
        actions[op].f(ip)


def catalog(request):
    """List view for Cyclades ips."""
    context = {}
    context['action_dict'] = get_permitted_actions(request.user)
    context['filter_dict'] = IPFilterSet().filters.itervalues()
    context['columns'] = ["ID", "Address", "Floating",
                          "Creation date", "User ID", ""]
    context['item_type'] = 'ip'

    return context


def details(request, query):
    """Details view for Astakos users."""
    error = request.GET.get('error', None)

    ip = IPAddress.objects.get(pk=int(query))
    vm_list = [ip.nic.machine]
    network_list = [ip.nic.network]
    nic_list = [ip.nic]
    user_list = AstakosUser.objects.filter(uuid=ip.userid)
    project_list = Project.objects.filter(uuid=ip.project)

    context = {
        'main_item': ip,
        'main_type': 'ip',
        'associations_list': [
            (vm_list, 'vm'),
            (network_list, 'network'),
            (nic_list, 'nic'),
            (user_list, 'user'),
            (project_list, 'project'),
        ]
    }

    return context
