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

from synnefo_admin.admin.actions import (has_permission_or_403,
                                         get_allowed_actions,
                                         get_permitted_actions,)
from synnefo_admin.admin.utils import get_actions, render_email
from synnefo_admin.admin.users.utils import get_user

from .utils import get_contact_email, get_contact_name
from .actions import cached_actions
from .filters import IPFilterSet


templates = {
    'list': 'admin/ip_list.html',
    'details': 'admin/ip_details.html',
}


class IPJSONView(DatatablesView):
    model = IPAddress
    fields = ('pk', 'address', 'floating_ip', 'created', 'userid',)
    filters = IPFilterSet

    def get_extra_data(self, qs):
        # FIXME: The `contact_name`, `contact_email` fields will cripple our db
        if self.form.cleaned_data['iDisplayLength'] < 0:
            qs = qs.only('pk', 'address', 'floating_ip', 'created', 'userid',)
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
            'value': inst.address,
            'visible': False,
        }
        extra_dict['details_url'] = {
            'display_name': "Details",
            'value': reverse('admin-details', args=['ip', inst.pk]),
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
            'visible': True,
        }
        extra_dict['contact_name'] = {
            'display_name': "Contact name",
            'value': get_contact_name(inst),
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
        extra_dict['updated'] = {
            'display_name': "Update date",
            'value': inst.updated,
            'visible': True,
        }
        extra_dict['in_use'] = {
            'display_name': "Currently in Use",
            'value': inst.in_use(),
            'visible': True,
        }
        extra_dict['network_info'] = {
            'display_name': "Network info",
            'value': ('ID: ' + str(inst.network.id) + ', Name: ' +
                      str(inst.network.id)),
            'visible': True,
        }

        return extra_dict


@has_permission_or_403(cached_actions)
def do_action(request, op, id):
    """Apply the requested action on the specified ip."""
    if op == "contact":
        user = get_user(id)
    else:
        ip = IPAddress.objects.get(id=id)
    actions = get_permitted_actions(cached_actions, request.user)

    if op == 'contact':
        subject, body = render_email(request.POST, user)
        actions[op].f(user, subject, template_name=None, text=body)
    else:
        actions[op].f(ip)


def catalog(request):
    """List view for Cyclades ips."""
    context = {}
    context['action_dict'] = get_permitted_actions(cached_actions, request.user)
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
        'action_dict': get_permitted_actions(cached_actions, request.user),
        'associations_list': [
            (vm_list, 'vm', get_actions("vm", request.user)),
            (network_list, 'network', get_actions("network", request.user)),
            (nic_list, 'nic', None),
            (user_list, 'user', get_actions("user", request.user)),
            (project_list, 'project', get_actions("project", request.user)),
        ]
    }

    return context
