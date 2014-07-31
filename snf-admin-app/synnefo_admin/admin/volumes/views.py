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
from django.utils.html import escape

from synnefo.db.models import Volume, VirtualMachine
from astakos.im.models import AstakosUser, Project

from synnefo_admin.admin.actions import (has_permission_or_403,
                                         get_allowed_actions,
                                         get_permitted_actions,)
from synnefo_admin.admin.users.utils import get_user_or_404
from synnefo_admin.admin.tables import AdminJSONView
from synnefo_admin.admin.associations import (
    UserAssociation, QuotaAssociation, VMAssociation, VolumeAssociation,
    NetworkAssociation, NicAssociation, IPAssociation, IPLogAssociation,
    ProjectAssociation)

from .utils import (get_volume_or_404, get_user_details_href,
                    get_vm_details_href, get_project_details_href)
from .actions import cached_actions
from .filters import VolumeFilterSet

templates = {
    'list': 'admin/volume_list.html',
    'details': 'admin/volume_details.html',
}


class VolumeJSONView(AdminJSONView):
    model = Volume
    fields = ('id', 'name', 'status', 'size', 'volume_type__disk_template',
              'machine__pk', 'created', 'updated')
    filters = VolumeFilterSet

    def format_data_row(self, row):
        row = list(row)
        if not row[1]:
            row[1] = "(not set)"
        row[6] = row[6].strftime("%Y-%m-%d %H:%M")
        row[7] = row[7].strftime("%Y-%m-%d %H:%M")
        return row

    def get_extra_data(self, qs):
        # FIXME: The `contact_name`, `contact_email` fields will cripple our db
        if self.form.cleaned_data['iDisplayLength'] < 0:
            qs = qs.only('id', 'name', 'status', 'created', 'userid')
        return [self.get_extra_data_row(row) for row in qs]

    def get_extra_data_row(self, inst):
        if self.dt_data['iDisplayLength'] < 0:
            extra_dict = {}
        else:
            extra_dict = OrderedDict()

        extra_dict['allowed_actions'] = {
            'display_name': "",
            'value': get_allowed_actions(cached_actions, inst,
                                         self.request.user),
            'visible': False,
        }
        extra_dict['id'] = {
            'display_name': "ID",
            'value': inst.id,
            'visible': False,
        }
        extra_dict['item_name'] = {
            'display_name': "Name",
            'value': escape(inst.name),
            'visible': False,
        }
        extra_dict['details_url'] = {
            'display_name': "Details",
            'value': reverse('admin-details', args=['volume', inst.id]),
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
        extra_dict['description'] = {
            'display_name': "Description",
            'value': escape(inst.description) or "(not set)",
            'visible': True,
        }
        sv = inst.source_version
        source_version = " (v{})".format(sv) if sv else ""
        extra_dict['source'] = {
            'display_name': "Source Image",
            'value': inst.source + source_version,
            'visible': True,
        }
        extra_dict['origin'] = {
            'display_name': "Origin",
            'value': inst.origin,
            'visible': True,
        }
        extra_dict['index'] = {
            'display_name': "Index",
            'value': inst.index,
            'visible': True,
        }
        extra_dict['user_info'] = {
            'display_name': "User",
            'value': get_user_details_href(inst),
            'visible': True,
        }
        extra_dict['project_info'] = {
            'display_name': "Project",
            'value': get_project_details_href(inst),
            'visible': True,
        }
        if inst.machine:
            extra_dict['vm_info'] = {
                'display_name': "VM",
                'value': get_vm_details_href(inst),
                'visible': True,
            }
        return extra_dict


@has_permission_or_403(cached_actions)
def do_action(request, op, id):
    """Apply the requested action on the specified volume."""
    if op == "contact":
        user = get_user_or_404(id)
    else:
        volume = Volume.objects.get(id=id)
    actions = get_permitted_actions(cached_actions, request.user)

    if op == 'contact':
        actions[op].apply(user, request)
    else:
        actions[op].apply(volume)


def catalog(request):
    """List view for Cyclades volumes."""
    context = {}
    context['action_dict'] = get_permitted_actions(cached_actions, request.user)
    context['filter_dict'] = VolumeFilterSet().filters.itervalues()
    context['columns'] = ["ID", "Name", "Status", "Size (GB)", "Disk template",
                          "VM ID", "Created at", "Updated at", ""]
    context['item_type'] = 'volume'

    return context


def details(request, query):
    """Details view for Astakos users."""
    volume = get_volume_or_404(query)
    associations = []

    vm_list = VirtualMachine.objects.filter(volumes=volume)
    associations.append(VMAssociation(request, vm_list,))

    user_list = AstakosUser.objects.filter(uuid=volume.userid)
    associations.append(UserAssociation(request, user_list,))

    project_list = Project.objects.filter(uuid=volume.project)
    associations.append(ProjectAssociation(request, project_list,))

    context = {
        'main_item': volume,
        'main_type': 'volume',
        'action_dict': get_permitted_actions(cached_actions, request.user),
        'associations_list': associations,
    }

    return context
