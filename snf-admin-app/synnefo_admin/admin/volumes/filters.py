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
from synnefo_admin.admin.utils import (filter_owner_name, filter_id,
                                       filter_vm_id)


class VolumeFilterSet(django_filters.FilterSet):

    """A collection of filters for volumes.

    This filter collection is based on django-filter's FilterSet.
    """

    volumeid = django_filters.CharFilter(label='Volume ID',
                                         lookup_type='icontains',
                                         action=filter_id('id'))
    name = django_filters.CharFilter(label='Name', lookup_type='icontains')
    owner_name = django_filters.CharFilter(label='Owner Name',
                                           action=filter_owner_name)
    userid = django_filters.CharFilter(label='Owner UUID',
                                       lookup_type='icontains')
    status = django_filters.MultipleChoiceFilter(
        label='Status', name='status', choices=Volume.STATUS_VALUES)
    machineid = django_filters.CharFilter(label='VM ID',
                                          action=filter_vm_id('machine__id'))

    class Meta:
        model = Volume
        fields = ('volumeid', 'name', 'status', 'description', 'owner_name',
                  'userid', 'machineid')
