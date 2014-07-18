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

from operator import or_

from django.core.urlresolvers import reverse
from django.db.models import Q
from django.conf import settings

from synnefo.db.models import (VirtualMachine, Network, Volume, IPAddress,
                               IPAddressLog)
from astakos.im.models import AstakosUser, ProjectMembership, Project
from astakos.im.user_utils import send_plain as send_email

from synnefo.logic import servers as servers_backend
from synnefo.logic.commands import validate_server_action

from eztables.views import DatatablesView

import django_filters

from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from synnefo_admin.admin.utils import filter_owner_name, filter_vm_id
from synnefo_admin.admin.queries_common import (query, model_filter,
                                                get_model_field)


@model_filter
def filter_vm(queryset, queries):
    q = query("vm", queries)
    return queryset.filter(q)


@model_filter
def filter_user(queryset, queries):
    q = query("user", queries)
    ids = get_model_field("user", q, 'uuid')
    return queryset.filter(userid__in=ids)


@model_filter
def filter_volume(queryset, queries):
    q = query("volume", queries)
    ids = get_model_field("volume", q, 'machine__id')
    return queryset.filter(id__in=ids)


@model_filter
def filter_network(queryset, queries):
    q = query("network", queries)
    ids = get_model_field("network", q, 'machines__id')
    return queryset.filter(id__in=ids)


@model_filter
def filter_ip(queryset, queries):
    q = query("ip", queries)
    ids = get_model_field("ip", q, 'machines__id')
    return queryset.filter(id__in=ids)


@model_filter
def filter_project(queryset, queries):
    q = query("project", queries)
    ids = get_model_field("project", q, 'uuid')
    return queryset.filter(project__in=ids)


def filter_id(field):
    def _filter_id(qs, query):
        if not query:
            return qs
        return qs.filter(**{"%s__icontains" % field: int(query)})

    return _filter_id


class VMFilterSet(django_filters.FilterSet):

    """A collection of filters for VMs.

    This filter collection is based on django-filter's FilterSet.
    """

    vm = django_filters.CharFilter(label='VM', action=filter_vm)
    user = django_filters.CharFilter(label='OF User', action=filter_user)
    vol = django_filters.CharFilter(label='HAS Volume', action=filter_volume)
    net = django_filters.CharFilter(label='IN Network', action=filter_network)
    proj = django_filters.CharFilter(label='OF Project', action=filter_project)
    operstate = django_filters.MultipleChoiceFilter(
        label='Status', name='operstate', choices=VirtualMachine.OPER_STATES)

    class Meta:
        model = VirtualMachine
        fields = ('vm', 'operstate', 'suspended', 'user', 'vol', 'net', 'proj')
