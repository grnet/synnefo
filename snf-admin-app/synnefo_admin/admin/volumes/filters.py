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
from synnefo_admin.admin.queries_common import (query, model_filter,
                                                get_model_field)


@model_filter
def filter_volume(queryset, queries):
    q = query("volume", queries)
    return queryset.filter(q)


@model_filter
def filter_user(queryset, queries):
    q = query("user", queries)
    ids = get_model_field("user", q, 'uuid')
    return queryset.filter(userid__in=ids)


@model_filter
def filter_vm(queryset, queries):
    q = query("vm", queries)
    ids = get_model_field("vm", q, 'volumes__id')
    return queryset.filter(id__in=ids)


@model_filter
def filter_project(queryset, queries):
    q = query("project", queries)
    ids = get_model_field("project", q, 'uuid')
    return queryset.filter(project__in=ids)


class VolumeFilterSet(django_filters.FilterSet):

    """A collection of filters for volumes.

    This filter collection is based on django-filter's FilterSet.
    """

    volume = django_filters.CharFilter(label='Volume', action=filter_volume)
    user = django_filters.CharFilter(label='OF User', action=filter_user)
    vm = django_filters.CharFilter(label='OF VM', action=filter_vm)
    project = django_filters.CharFilter(label='OF Project',
                                        action=filter_project)
    status = django_filters.MultipleChoiceFilter(
        label='Status', name='status', choices=Volume.STATUS_VALUES)

    class Meta:
        model = Volume
        fields = ('volume', 'status', 'user', 'vm', 'project')
