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

from synnefo_admin.admin.utils import is_resource_useful, filter_id

from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from synnefo_admin.admin.queries_common import (query, model_filter,
                                                get_model_field)


@model_filter
def filter_project(queryset, queries):
    q = query("project", queries)
    return queryset.filter(q)


@model_filter
def filter_user(queryset, queries):
    q = query("user", queries)
    ids = get_model_field("user", q, 'uuid')
    qor = Q(members__uuid__in=ids) | Q(owner__uuid__in=ids)
    return queryset.filter(qor)


@model_filter
def filter_vm(queryset, queries):
    q = query("vm", queries)
    ids = get_model_field("vm", q, 'project')
    return queryset.filter(uuid__in=ids)


@model_filter
def filter_volume(queryset, queries):
    q = query("volume", queries)
    ids = get_model_field("volume", q, 'project')
    return queryset.filter(uuid__in=ids)


@model_filter
def filter_network(queryset, queries):
    q = query("network", queries)
    ids = get_model_field("network", q, 'project')
    return queryset.filter(uuid__in=ids)


@model_filter
def filter_ip(queryset, queries):
    q = query("ip", queries)
    ids = get_model_field("ip", q, 'project')
    return queryset.filter(uuid__in=ids)


def get_status_choices():
    """Get all possible project statuses from Project model."""
    project_states = Project.O_STATE_DISPLAY.itervalues()
    return [(value.upper(), '_') for value in project_states]


def filter_status(queryset, choices):
    """Filter project status.

    Filter by project and last application status.
    """
    choices = choices or ()
    if len(choices) == len(get_status_choices()):
        return queryset
    q = Q()
    for c in choices:
        status = getattr(Project, 'O_%s' % c.upper())
        q |= Q(last_application__state=status) | Q(state=status)
    return queryset.filter(q).distinct()


class ProjectFilterSet(django_filters.FilterSet):

    """A collection of filters for Projects.

    This filter collection is based on django-filter's FilterSet.
    """

    project = django_filters.CharFilter(label='Project', action=filter_project)
    user = django_filters.CharFilter(label='OF User', action=filter_user)
    vm = django_filters.CharFilter(label='HAS VM', action=filter_vm)
    volume = django_filters.CharFilter(label='HAS Volume',
                                       action=filter_volume)
    net = django_filters.CharFilter(label='HAS Network', action=filter_network)
    ip = django_filters.CharFilter(label='HAS IP', action=filter_ip)
    status = django_filters.MultipleChoiceFilter(
        label='Status', action=filter_status, choices=get_status_choices())
    is_base = django_filters.BooleanFilter(label='System')

    class Meta:
        model = Project
        fields = ('project', 'status', 'is_base', 'user', 'vm', 'volume',
                  'net', 'ip',)
