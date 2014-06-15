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

from synnefo.db.models import (VirtualMachine, Network, Volume,
                               NetworkInterface, IPAddress)
from astakos.im.models import (AstakosUser, Project, ProjectResourceGrant,
                               Resource)

from eztables.views import DatatablesView
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

from synnefo_admin.admin.utils import is_resource_useful

from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from .filters import ProjectFilterSet
from .actions import (generate_actions, get_allowed_actions,
                      get_permitted_actions)
from .utils import (get_contact_id, get_contact_name, get_contact_mail,
                    get_project, display_project_stats,
                    display_project_resources,)


templates = {
    'list': 'admin/project_list.html',
    'details': 'admin/project_details.html',
}


class ProjectJSONView(DatatablesView):
    model = Project
    fields = ('id', 'realname', 'state', 'creation_date', 'end_date')

    extra = True
    filters = ProjectFilterSet

    def format_data_row(self, row):
        row[2] = (str(row[2]) + ' (' +
                  Project.objects.get(id=row[0]).state_display() + ')')
        row[3] = str(row[3].date())
        row[4] = str(row[4].date())
        return row

    def get_extra_data_row(self, inst):
        extra_dict = OrderedDict()
        extra_dict['allowed_actions'] = {
            'display_name': "",
            'value': get_allowed_actions(inst),
            'visible': False,
        }
        extra_dict['id'] = {
            'display_name': "ID",
            'value': inst.id,
            'visible': False,
        }
        extra_dict['item_name'] = {
            'display_name': "Name",
            'value': inst.realname,
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
        extra_dict['contact_mail'] = {
            'display_name': "Contact mail",
            'value': get_contact_mail(inst),
            'visible': False,
        }
        extra_dict['contact_name'] = {
            'display_name': "Contact name",
            'value': get_contact_name(inst),
            'visible': False,
        }
        extra_dict['uuid'] = {
            'display_name': "UUID",
            'value': inst.uuid,
            'visible': False,
        }

        if not inst.is_base:
            extra_dict['homepage'] = {
                'display_name': "Homepage",
                'value': inst.homepage,
                'visible': True,
            }

            extra_dict['description'] = {
                'display_name': "Description",
                'value': inst.description,
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
                    'value': inst.last_application.comments,
                    'visible': True,
                }

            extra_dict['member_resources'] = {
                'display_name': "Member resource limits",
                'value': display_project_resources(inst, 'member'),
                'visible': True
            }

        extra_dict['limit'] = {
            'display_name': "Total resource limits",
            'value': display_project_resources(inst, 'total'),
            'visible': True,
        }
        extra_dict['usage'] = {
            'display_name': "Total resource usage",
            'value': display_project_stats(inst, 'project_usage'),
            'visible': True,
        }

        return extra_dict


@has_permission_or_403(generate_actions())
def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    project = get_project(id)
    actions = get_permitted_actions(request.user)
    logging.info("Op: %s, project: %s, fun: %s", op, project.uuid,
                 actions[op].f)

    if op == 'contact':
        if project.is_base:
            user = project.members.all()[0]
        else:
            user = project.owner
        actions[op].f(user, request.POST['text'])
    elif op == 'approve':
        actions[op].f(project.last_application.id)
    else:
        actions[op].f(project)


def catalog(request):
    """List view for Cyclades projects."""
    context = {}
    context['action_dict'] = get_permitted_actions(request.user)
    context['filter_dict'] = ProjectFilterSet().filters.itervalues()
    context['columns'] = ["ID", "Name", "Status", "Creation date",
                          "Expiration date", ""]
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
        'associations_list': [
            (user_list, 'user'),
            (vm_list, 'vm'),
            (volume_list, 'volume'),
            (network_list, 'network'),
            (ip_list, 'ip'),
        ]
    }

    return context
