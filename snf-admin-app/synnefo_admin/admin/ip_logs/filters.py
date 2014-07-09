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

from synnefo.db.models import IPAddressLog, VirtualMachine
from synnefo.logic import ips
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView
import django_filters

from synnefo_admin.admin.utils import (filter_owner_name, filter_owner_email,
                                       filter_id, filter_vm_id)


def filter_user_name(queryset, query):
    if not query:
        return queryset
    qs = VirtualMachine.objects.all()
    server_ids = filter_owner_name(qs, query).values('pk')
    return queryset.filter(server_id__in=server_ids).distinct()


def filter_user_email(queryset, query):
    if not query:
        return queryset
    qs = VirtualMachine.objects.all()
    server_ids = filter_owner_email(qs, query).values('pk')
    return queryset.filter(server_id__in=server_ids).distinct()


class IPLogFilterSet(django_filters.FilterSet):

    """A collection of filters for volumes.

    This filter collection is based on django-filter's FilterSet.
    """

    address = django_filters.CharFilter(label='Address',
                                        lookup_type='icontains')
    server_id = django_filters.CharFilter(label='VM ID',
                                          action=filter_vm_id('server_id'))
    network_id = django_filters.CharFilter(label='Network ID',
                                           action=filter_id('network_id'))
    user_name = django_filters.CharFilter(label='Owner Name',
                                          action=filter_user_name)
    user_email = django_filters.CharFilter(label='Owner Email',
                                           action=filter_user_email)

    class Meta:
        model = IPAddressLog
        fields = ('address', 'server_id', 'network_id', 'user_name',
                  'user_email')
