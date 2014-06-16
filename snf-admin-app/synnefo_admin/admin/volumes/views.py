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
from collections import OrderedDict

from django.core.urlresolvers import reverse

from synnefo.db.models import Volume
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
from synnefo_admin.admin.networks.actions import get_permitted_actions as \
    get_network_actions
from synnefo_admin.admin.ips.actions import get_permitted_actions as \
    get_ip_actions
from synnefo_admin.admin.projects.actions import get_permitted_actions as \
    get_project_actions


from .utils import get_volume
from .filters import VolumeFilterSet
from .actions import (generate_actions, get_allowed_actions,
                      get_permitted_actions)

templates = {
    'list': 'admin/volume_list.html',
    'details': 'admin/volume_details.html',
}


class VolumeJSONView(DatatablesView):
    model = Volume
    fields = ('id',
              'name',
              'status',
              'created',
              'machine__pk',
              )

    extra = True
    filters = VolumeFilterSet

    def format_data_row(self, row):
        if not row[1]:
            row[1] = "(not set)"
        return row

    def get_extra_data_row(self, inst):
        extra_dict = OrderedDict()
        extra_dict = {
            'allowed_actions': {
                'display_name': "",
                'value': get_allowed_actions(inst),
                'visible': False,
            }, 'id': {
                'display_name': "ID",
                'value': inst.id,
                'visible': False,
            }, 'item_name': {
                'display_name': "Name",
                'value': inst.name,
                'visible': False,
            }, 'details_url': {
                'display_name': "Details",
                'value': reverse('admin-details', args=['volume', inst.id]),
                'visible': True,
            }, 'contact_id': {
                'display_name': "Contact ID",
                'value': inst.userid,
                'visible': False,
            }, 'contact_mail': {
                'display_name': "Contact mail",
                'value': AstakosUser.objects.get(uuid=inst.userid).email,
                'visible': False,
            }, 'contact_name': {
                'display_name': "Contact name",
                'value': AstakosUser.objects.get(uuid=inst.userid).realname,
                'visible': False,
            }, 'description': {
                'display_name': "Description",
                'value': inst.description or "(not set)",
                'visible': True,
            }, 'updated': {
                'display_name': "Update time",
                'value': inst.updated,
                'visible': True,
            }, 'user_info': {
                'display_name': "User info",
                'value': inst.userid,
                'visible': True,
            }
        }

        return extra_dict


@has_permission_or_403(generate_actions())
def do_action(request, op, id):
    """Apply the requested action on the specified volume."""
    volume = Volume.objects.get(id=id)
    actions = get_permitted_actions(request.user)

    if op == 'contact':
        actions[op].f(volume, request.POST['text'])
    else:
        actions[op].f(volume)


def catalog(request):
    """List view for Cyclades volumes."""
    context = {}
    context['action_dict'] = get_permitted_actions(request.user)
    context['filter_dict'] = VolumeFilterSet().filters.itervalues()
    context['columns'] = ["ID", "Name", "Status", "Creation date",
                          "VM ID", ""]
    context['item_type'] = 'volume'

    return context


def details(request, query):
    """Details view for Astakos users."""
    error = request.GET.get('error', None)

    volume = get_volume(query)
    vm_list = [volume.machine]
    user_list = AstakosUser.objects.filter(uuid=volume.userid)
    project_list = Project.objects.filter(uuid=volume.project)

    context = {
        'main_item': volume,
        'main_type': 'volume',
        'action_dict': get_permitted_actions(request.user),
        'associations_list': [
            (vm_list, 'vm', get_vm_actions(request.user)),
            (user_list, 'user', get_user_actions(request.user)),
            (project_list, 'project', get_project_actions(request.user)),
        ]
    }

    return context
