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
logger = logging.getLogger(__name__)
import re
from collections import OrderedDict

from operator import or_

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group
from django.utils.html import escape

from synnefo.db.models import (VirtualMachine, Network, IPAddressLog, Volume,
                               NetworkInterface, IPAddress)
from astakos.im.models import AstakosUser, ProjectMembership, Project, Resource
from astakos.im import user_logic as users

from astakos.im.user_utils import send_plain as send_email

from synnefo.util import units

import django_filters
from django.db.models import Q

from synnefo_admin.admin.actions import (has_permission_or_403,
                                         get_allowed_actions,
                                         get_permitted_actions,)
from synnefo_admin.admin.utils import (get_actions, render_email,
                                       create_details_href,)
from synnefo_admin.admin.tables import AdminJSONView

from .utils import (get_user, get_quotas, get_user_groups,
                    get_enabled_providers, get_suspended_vms, )
from .actions import cached_actions
from .filters import UserFilterSet

templates = {
    'list': 'admin/user_list.html',
    'details': 'admin/user_details.html',
}


class UserJSONView(AdminJSONView):
    model = AstakosUser
    fields = ('email', 'first_name', 'last_name', 'is_active',
              'is_rejected', 'moderated', 'email_verified')
    filters = UserFilterSet

    def get_extra_data(self, qs):
        if self.form.cleaned_data['iDisplayLength'] < 0:
            qs = qs.only('email', 'first_name', 'last_name', 'is_active',
                         'is_rejected', 'moderated', 'email_verified', 'uuid')
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
            'display_name': "UUID",
            'value': inst.uuid,
            'visible': True,
        }
        extra_dict['item_name'] = {
            'display_name': "Name",
            'value': escape(inst.realname),
            'visible': False,
        }
        extra_dict['details_url'] = {
            'display_name': "Details",
            'value': reverse('admin-details', args=['user', inst.uuid]),
            'visible': True,
        }
        extra_dict['contact_id'] = {
            'display_name': "Contact ID",
            'value': inst.uuid,
            'visible': False,
        }
        extra_dict['contact_email'] = {
            'display_name': "Contact email",
            'value': escape(inst.email),
            'visible': False,
        }
        extra_dict['contact_name'] = {
            'display_name': "Contact name",
            'value': escape(inst.realname),
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
        extra_dict['status'] = {
            'display_name': "Status",
            'value': inst.status_display,
            'visible': True,
        }
        extra_dict['groups'] = {
            'display_name': "Groups",
            'value': escape(get_user_groups(inst)),
            'visible': True,
        }
        extra_dict['enabled_providers'] = {
            'display_name': "Enabled providers",
            'value': get_enabled_providers(inst),
            'visible': True,
        }

        if (users.validate_user_action(inst, "ACCEPT") and
                inst.verification_code):
            extra_dict['activation_url'] = {
                'display_name': "Activation URL",
                'value': inst.get_activation_url(),
                'visible': True,
            }

        if inst.accepted_policy:
            extra_dict['moderation_policy'] = {
                'display_name': "Moderation policy",
                'value': inst.accepted_policy,
                'visible': True,
            }

        suspended_vms = get_suspended_vms(inst)

        extra_dict['suspended_vms'] = {
            'display_name': "Suspended VMs",
            'value': suspended_vms,
            'visible': True,
        }

        return extra_dict


@has_permission_or_403(cached_actions)
def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    user = get_user(id)
    actions = get_permitted_actions(cached_actions, request.user)
    logging.info("Op: %s, target: %s, fun: %s", op, user.email, actions[op].f)

    if op == 'reject':
        actions[op].f(user, 'Rejected by the admin')
    elif op == 'contact':
        subject, body = render_email(request.POST, user)
        actions[op].f(user, subject, template_name=None, text=body)
    else:
        actions[op].f(user)


def catalog(request):
    """List view for Astakos users."""

    context = {}
    context['action_dict'] = get_permitted_actions(cached_actions, request.user)
    context['filter_dict'] = UserFilterSet().filters.itervalues()
    context['columns'] = ["E-mail", "First Name", "Last Name", "Active",
                          "Rejected", "Moderated", "Verified", ""]
    context['item_type'] = 'user'

    return context


def details(request, query):
    """Details view for Astakos users."""
    user = get_user(query)
    quota_list = get_quotas(user)

    qor = Q(members=user) | Q(last_application__applicant=user)
    project_list = Project.objects.filter(qor)

    vm_list = VirtualMachine.objects.filter(userid=user.uuid)

    volume_list = Volume.objects.filter(userid=user.uuid)

    qor = Q(public=True, nics__machine__userid=user.uuid) | Q(userid=user.uuid)
    network_list = Network.objects.filter(qor)

    nic_list = NetworkInterface.objects.filter(userid=user.uuid)

    ip_list = IPAddress.objects.filter(userid=user.uuid)

    qor = [Q(server_id=vm.pk) for vm in vm_list]
    ip_log_list = []
    if qor:
        qor = reduce(or_, qor)
        ip_log_list = IPAddressLog.objects.filter(qor).order_by("allocated_at")

    for ipaddr in ip_log_list:
        ipaddr.ip = IPAddress.objects.get(address=ipaddr.address)
        ipaddr.vm = VirtualMachine.objects.get(id=ipaddr.server_id)
        ipaddr.network = Network.objects.get(id=ipaddr.network_id)
        ipaddr.user = user

    context = {
        'main_item': user,
        'main_type': 'user',
        'action_dict': get_permitted_actions(cached_actions, request.user),
        'associations_list': [
            (quota_list, 'quota', None),
            (project_list, 'project', get_actions("project", request.user)),
            (vm_list, 'vm', get_actions("vm", request.user)),
            (volume_list, 'volume', get_actions("volume", request.user)),
            (network_list, 'network', get_actions("network", request.user)),
            (nic_list, 'nic', None),
            (ip_list, 'ip', get_actions("ip", request.user)),
            (ip_log_list, 'ip_log', None),
        ]
    }

    return context
