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
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from synnefo.db.models import Volume
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView

import django_filters

from synnefo_admin.admin.exceptions import AdminHttp404
from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from synnefo_admin.admin.utils import create_details_href


def get_volume_or_404(query):
    try:
        return Volume.objects.get(pk=int(query))
    except (ObjectDoesNotExist, ValueError):
        raise AdminHttp404(
            "No Volume was found that matches this query: %s\n" % query)


def get_user_details_href(volume):
    user = AstakosUser.objects.get(uuid=volume.userid)
    return create_details_href('user', user.realname, user.email)


def get_vm_details_href(volume):
    vm = volume.machine
    return create_details_href('vm', vm.name, vm.id)
