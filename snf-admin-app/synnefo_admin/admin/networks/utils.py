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
from django.http import Http404
from django.conf import settings
from django.core.urlresolvers import reverse

from synnefo.db.models import (Network, VirtualMachine, NetworkInterface,
                               IPAddress)
from synnefo.logic.networks import validate_network_action
from synnefo.logic import networks
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView
import django_filters

from synnefo_admin.admin.exceptions import AdminHttp404
from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from synnefo_admin.admin.utils import filter_owner_name, create_details_href


def get_network_or_404(query):
    try:
        return Network.objects.get(pk=int(query))
    except (ObjectDoesNotExist, ValueError):
        raise AdminHttp404(
            "No Network was found that matches this query: %s\n" % query)


def get_contact_email(inst):
    if inst.userid:
        return AstakosUser.objects.get(uuid=inst.userid).email,
    else:
        return "-"


def get_contact_name(inst):
    if inst.userid:
        return AstakosUser.objects.get(uuid=inst.userid).realname,
    else:
        return "-"


def get_user_details_href(inst):
    if inst.userid:
        user = AstakosUser.objects.get(uuid=inst.userid)
        return create_details_href('user', user.realname, user.email)
    else:
        return "-"
