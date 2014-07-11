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
from operator import itemgetter

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.html import escape

from synnefo.db.models import (VirtualMachine, Network, Volume,
                               NetworkInterface, IPAddress)
from astakos.im.models import (AstakosUser, Project, ProjectResourceGrant,
                               Resource)

from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from astakos.im.user_utils import send_plain as send_email
from astakos.im.functions import (validate_project_action, ProjectConflict,
                                  approve_application, deny_application,
                                  suspend, unsuspend, terminate, reinstate)
from astakos.im.quotas import get_project_quota

from synnefo.util import units

import django_filters
from django.db.models import Q

from synnefo_admin.admin.utils import (is_resource_useful, get_actions,
                                       render_email)

from synnefo_admin.admin.actions import (has_permission_or_403,
                                         get_allowed_actions,
                                         get_permitted_actions,)
from synnefo_admin.admin.users.utils import get_user
from synnefo_admin.admin.tables import AdminJSONView

from .filters import ProjectFilterSet
from .actions import cached_actions
from .utils import (get_contact_id, get_contact_name, get_contact_email,
                    get_project, display_project_usage_horizontally,
                    display_member_quota_horizontally,
                    display_project_limit_horizontally)


templates = {
    'list': 'admin/project_list.html',
    'details': 'admin/project_details.html',
}


class ProjectJSONView(AdminJSONView):
    model = Project
    fields = ('id', 'realname', '{owner__first_name} {owner__last_name}',
              'state', 'creation_date', 'end_date')
    filters = ProjectFilterSet

    def format_data_row(self, row):
        if self.dt_data['iDisplayLength'] > 0:
            row = list(row)
            if row[2] == "None None":
                row[2] = "(not set)"
            row[3] = (str(row[3]) + ' (' +
                      Project.objects.get(id=row[0]).state_display() + ')')
            row[4] = str(row[4].date())
            row[5] = str(row[5].date())
        return row

    def get_extra_data(self, qs):
        if self.form.cleaned_data['iDisplayLength'] < 0:
            qs = qs.only('id', 'realname', 'state', 'is_base',
                         'uuid',).select_related('last_application__state',
                                                 'last_application__id',
                                                 'owner__id', 'owner__uuid')
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
            'value': escape(inst.realname),
            'visible': False,
        }
        extra_dict['details_url'] = {
            'display_name': "Details",
            'value': reverse('admin-details', args=['project', inst.id]),
            'visible': True,
        }
        extra_dict['contact_id'] = {
            'display_name': "Contact ID",
            'value': get_contact_id(inst),
            'visible': False,
        }
        extra_dict['contact_email'] = {
            'display_name': "Contact email",
            'value': escape(get_contact_email(inst)),
            'visible': False,
        }
        extra_dict['contact_name'] = {
            'display_name': "Contact name",
            'value': escape(get_contact_name(inst)),
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
        extra_dict['uuid'] = {
            'display_name': "UUID",
            'value': inst.uuid,
            'visible': False,
        }

        if not inst.is_base:
            extra_dict['homepage'] = {
                'display_name': "Homepage url",
                'value': escape(inst.homepage) or "(not set)",
                'visible': True,
            }

            extra_dict['description'] = {
                'display_name': "Description",
                'value': escape(inst.description) or "(not set)",
                'visible': True,
            }
            extra_dict['members'] = {
                'display_name': "Members",
                'value': (str(inst.members_count()) + ' / ' +
                          str(inst.limit_on_members_number)),
                'visible': True,
            }

            if inst.last_application.comments:
                extra_dict['comments'] = {
                    'display_name': "Comments for review",
                    'value': escape(inst.last_application.comments) or "(not set)",
                    'visible': True,
                }

            extra_dict['member_resources'] = {
                'display_name': "Max resources per member",
                'value': display_member_quota_horizontally(inst),
                'visible': True
            }

        extra_dict['limit'] = {
            'display_name': "Total resources",
            'value': display_project_limit_horizontally(inst),
            'visible': True,
        }
        extra_dict['usage'] = {
            'display_name': "Resource usage",
            'value': display_project_usage_horizontally(inst),
            'visible': True,
        }

        return extra_dict


@has_permission_or_403(cached_actions)
def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    if op == "contact":
        user = get_user(id)
    else:
        project = get_project(id)
    actions = get_permitted_actions(cached_actions, request.user)

    if op == 'contact':
        subject, body = render_email(request.POST, user)
        actions[op].f(user, subject, template_name=None, text=body)
    elif op == 'approve':
        actions[op].f(project.last_application.id)
    elif op == 'deny':
        actions[op].f(project.last_application.id)
    else:
        actions[op].f(project.id)


def catalog(request):
    """List view for Cyclades projects."""
    context = {}
    context['action_dict'] = get_permitted_actions(cached_actions, request.user)
    context['filter_dict'] = ProjectFilterSet().filters.itervalues()
    context['columns'] = ["ID", "Name", "Owner Name", "Status",
                          "Creation date", "End date", ""]
    context['item_type'] = 'project'

    return context


def details(request, query):
    """Details view for Astakos projects."""
    project = get_project(query)

    user_list = project.members.all()
    vm_list = VirtualMachine.objects.filter(project=project.uuid)
    volume_list = Volume.objects.filter(project=project.uuid)
    network_list = Network.objects.filter(project=project.uuid)
    ip_list = IPAddress.objects.filter(project=project.uuid)

    context = {
        'main_item': project,
        'main_type': 'project',
        'action_dict': get_permitted_actions(cached_actions, request.user),
        'associations_list': [
            (user_list, 'user', get_actions("user", request.user)),
            (vm_list, 'vm', get_actions("vm", request.user)),
            (volume_list, 'volume', get_actions("volume", request.user)),
            (network_list, 'network', get_actions("network", request.user)),
            (ip_list, 'ip', get_actions("ip", request.user)),
        ]
    }

    return context
