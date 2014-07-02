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

from synnefo.db.models import IPAddress, IPAddressLog, VirtualMachine, Network
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

from .utils import (get_user_details_href, get_ip_details_href,
                    get_vm_details_href, get_network_details_href)
from .filters import IPLogFilterSet


templates = {
    'list': 'admin/ip_log_list.html',
}


class IPLogJSONView(DatatablesView):
    model = IPAddressLog
    fields = ('address', 'server_id', 'network_id', 'allocated_at',
              'released_at', 'active',)
    filters = IPLogFilterSet

    def format_data_row(self, row):
        row = list(row)
        row[3] = row[3].strftime("%Y-%m-%d %H:%M")
        if row[4]:
            row[4] = row[4].strftime("%Y-%m-%d %H:%M")
        else:
            row[4] = "-"
        return row

    def get_extra_data_row(self, inst):
        extra_dict = OrderedDict()
        extra_dict['id'] = {
            'display_name': "ID",
            'value': inst.pk,
            'visible': False,
        }
        extra_dict['ip_info'] = {
            'display_name': "IP",
            'value': get_ip_details_href(inst),
            'visible': True,
        }
        extra_dict['vm_info'] = {
            'display_name': "VM",
            'value': get_vm_details_href(inst),
            'visible': True,
        }
        extra_dict['network_info'] = {
            'display_name': "Network",
            'value': get_network_details_href(inst),
            'visible': True,
        }
        extra_dict['user_info'] = {
            'display_name': "User",
            'value': get_user_details_href(inst),
            'visible': True,
        }

        return extra_dict


def catalog(request):
    """List view for Cyclades ips."""
    context = {}
    context['action_dict'] = None
    context['filter_dict'] = IPLogFilterSet().filters.itervalues()
    context['columns'] = ["Address", "Server ID", "Network ID",
                          "Allocation date", "Release date", "Active", ""]
    context['item_type'] = 'ip_log'

    return context
