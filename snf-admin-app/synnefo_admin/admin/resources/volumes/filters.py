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

from django.core.cache import cache
from django.db.models import Q

from synnefo.db.models import Volume

import django_filters

from synnefo_admin.admin.queries_common import (query, model_filter,
                                                get_model_field)


def get_disk_template_choices():
    # Check if the choices exist in the cache.
    dt_choices = cache.get('dt_choices')
    if dt_choices:
        return dt_choices

    # Recreate them if they don't.
    dt_choices = cache.get('dt_choices')
    dt_field = "volume_type__disk_template"
    dts = Volume.objects.order_by(dt_field).\
        values_list("{}".format(dt_field), flat=True).distinct()
    dt_choices = [(dt, '_') for dt in dts]

    # Store them in cache for 5 minutes and return them to the caller.
    cache.set('dt_choices', dt_choices, 300)
    return dt_choices


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


def filter_disk_template(queryset, choices):
    if not query:
        return queryset
    choices = choices or ()
    dt_choices = get_disk_template_choices()
    if len(choices) == len(dt_choices):
        return queryset
    q = Q()
    for c in choices:
        q |= Q(volume_type__disk_template=c)
    return queryset.filter(q)


def filter_index(queryset, query):
    if not query:
        return queryset
    elif not query.isdigit():
        return queryset.none()
    return queryset.filter(index=query)


class VolumeFilterSet(django_filters.FilterSet):

    """A collection of filters for volumes.

    This filter collection is based on django-filter's FilterSet.
    """

    vol = django_filters.CharFilter(label='Volume', action=filter_volume)
    user = django_filters.CharFilter(label='OF User', action=filter_user)
    vm = django_filters.CharFilter(label='OF VM', action=filter_vm)
    proj = django_filters.CharFilter(label='OF Project', action=filter_project)
    status = django_filters.MultipleChoiceFilter(
        label='Status', name='status', choices=Volume.STATUS_VALUES)
    disk_template = django_filters.MultipleChoiceFilter(
        label="Disk template", choices=get_disk_template_choices(),
        action=filter_disk_template)
    index = django_filters.CharFilter(label="Index", action=filter_index)
    source = django_filters.CharFilter(label="Soure image", name="source",
                                       lookup_type='icontains')

    class Meta:
        model = Volume
        fields = ('vol', 'status', 'disk_template', 'index', 'source',
                  'user', 'vm', 'proj')
