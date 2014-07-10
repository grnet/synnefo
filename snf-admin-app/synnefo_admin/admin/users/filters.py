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

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group
from django.template import Context, Template

from synnefo.db.models import (VirtualMachine, Network, IPAddressLog, Volume,
                               NetworkInterface, IPAddress)
from astakos.im.models import AstakosUser, ProjectMembership, Project, Resource
from astakos.im import user_logic as users

from astakos.im.user_utils import send_plain as send_email
from astakos.im import auth_providers

from synnefo.util import units

from eztables.views import DatatablesView

import django_filters
from django.db.models import Q

from synnefo_admin.admin.utils import filter_name
from .utils import get_groups

choice2query = {
    ('ACTIVE', ''): Q(is_active=True),
    ('INACTIVE', ''): Q(is_active=False, moderated=True) | Q(is_rejected=True),
    ('PENDING MODERATION', ''): Q(moderated=False, email_verified=True),
    ('PENDING EMAIL VERIFICATION', ''): Q(email_verified=False),
}


auth_providers = [(key, '_') for key in auth_providers.PROVIDERS.iterkeys()]


def filter_has_auth_providers(queryset, choices):
    choices = choices or ()
    q = Q()
    for c in choices:
        q |= Q(auth_providers__module=c)
    return queryset.filter(q).distinct()


def filter_has_not_auth_providers(queryset, choices):
    choices = choices or ()
    q = Q()
    for c in choices:
        q |= Q(auth_providers__module=c)
    return queryset.exclude(q).distinct()


def filter_status(queryset, choices):
    choices = choices or ()
    if len(choices) == len(choice2query.keys()):
        return queryset
    q = Q()
    for c in choices:
        q |= choice2query[(c, '')]
    return queryset.filter(q).distinct()


def filter_group(queryset, choices):
    """Filter by group name for user.

    Since not all users need to be in a group, we always process the request
    given even if all choices are selected.
    """
    choices = choices or ()
    q = Q()
    for c in choices:
        q |= Q(groups__name__exact=c)
    return queryset.filter(q).distinct()


class UserFilterSet(django_filters.FilterSet):

    """A collection of filters for users.

    This filter collection is based on django-filter's FilterSet.
    """

    uuid = django_filters.CharFilter(label='UUID', lookup_type='icontains',)
    email = django_filters.CharFilter(label='E-mail address',
                                      lookup_type='icontains',)
    name = django_filters.CharFilter(label='Name', action=filter_name,)
    status = django_filters.MultipleChoiceFilter(
        label='Status', action=filter_status, choices=choice2query.keys())
    groups = django_filters.MultipleChoiceFilter(
        label='Group', action=filter_group, choices=get_groups())
    has_auth_providers = django_filters.MultipleChoiceFilter(
        label='HAS Auth Providers', action=filter_has_auth_providers,
        choices=auth_providers)
    has_not_auth_providers = django_filters.MultipleChoiceFilter(
        label='HAS NOT Auth Providers', action=filter_has_not_auth_providers,
        choices=auth_providers)


    class Meta:
        model = AstakosUser
        fields = ('uuid', 'email', 'name', 'status', 'groups',
                  'has_auth_providers', 'has_not_auth_providers')
