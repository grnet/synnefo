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

import django_filters

from django.db.models import Q

from astakos.im.models import Project, ProjectApplication
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
    # BIG FAT FIXME: The below two lines in theory should not be necessary, but
    # if they don't exist, the queryset will produce weird results with the
    # addition of values list.
    qs = queryset.select_related("owner__uuid").filter(qor)
    len(qs)
    return qs


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


def get_project_status_choices():
    """Get all possible project statuses from Project model."""
    project_states = Project.O_STATE_DISPLAY.itervalues()
    return [(value.upper(), '_') for value in project_states]
project_status_choices = get_project_status_choices()


def get_application_status_choices():
    """Get all possible application statuses from ProjectApplication model."""
    app_states = ProjectApplication.APPLICATION_STATE_DISPLAY.itervalues()
    # There is a status with the name "Pending review". We only want to keep
    # the "Pending" part.
    return [(value.split()[0].upper(), '_') for value in app_states]
application_status_choices = get_application_status_choices()


def filter_project_status(queryset, choices):
    """Filter project status."""
    choices = choices or ()
    if not choices:
        return queryset
    if len(choices) == len(project_status_choices):
        return queryset
    q = Q()
    for c in choices:
        status = getattr(Project, 'O_%s' % c.upper())
        q |= Q(state=status)
    return queryset.filter(q).distinct()


def filter_application_status(queryset, choices):
    """Filter application status."""
    choices = choices or ()
    if not choices:
        return queryset
    if len(choices) == len(application_status_choices):
        return queryset
    q = Q()
    for c in choices:
        status = getattr(ProjectApplication, '%s' % c.upper())
        q |= Q(last_application__state=status)
    return queryset.filter(q).distinct()


class ProjectFilterSet(django_filters.FilterSet):

    """A collection of filters for Projects.

    This filter collection is based on django-filter's FilterSet.
    """

    proj = django_filters.CharFilter(label='Project', action=filter_project)
    user = django_filters.CharFilter(label='OF User', action=filter_user)
    vm = django_filters.CharFilter(label='HAS VM', action=filter_vm)
    vol = django_filters.CharFilter(label='HAS Volume', action=filter_volume)
    net = django_filters.CharFilter(label='HAS Network', action=filter_network)
    ip = django_filters.CharFilter(label='HAS IP', action=filter_ip)
    project_status = django_filters.MultipleChoiceFilter(
        label='Project Status', action=filter_project_status,
        choices=project_status_choices)
    application_status = django_filters.MultipleChoiceFilter(
        label='Application Status', action=filter_application_status,
        choices=application_status_choices)
    is_base = django_filters.BooleanFilter(label='System')

    class Meta:
        model = Project
        fields = ('proj', 'project_status', 'application_status', 'is_base',
                  'user', 'vm', 'vol', 'net', 'ip',)
