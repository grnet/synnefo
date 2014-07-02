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

from synnefo.db.models import IPAddress
from synnefo.logic import ips
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView

from synnefo_admin.admin.utils import create_details_href


def get_ip(query):
    if query.isdigit():
        ip = IPAddress.objects.get(pk=int(query))
    else:
        ip = IPAddress.objects.get(address=query)
    return ip


def get_contact_email(inst):
    if inst.userid:
        return AstakosUser.objects.get(uuid=inst.userid).email,


def get_contact_name(inst):
    if inst.userid:
        return AstakosUser.objects.get(uuid=inst.userid).realname,


def get_user_details_href(ip):
    if ip.userid:
        user = AstakosUser.objects.get(uuid=ip.userid)
        return create_details_href('user', user.realname, user.email)
    else:
        return "-"
