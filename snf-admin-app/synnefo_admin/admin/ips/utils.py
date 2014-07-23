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

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404

from synnefo.db.models import IPAddress, IPAddressLog
from synnefo.logic import ips
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView

from synnefo_admin.admin.exceptions import AdminHttp404
from synnefo_admin.admin.utils import create_details_href


def get_ip_or_404(query):
    try:
        return IPAddress.objects.get(address=query)
    except ObjectDoesNotExist:
        pass
    except MultipleObjectsReturned as e:
        raise AdminHttp404("Hm, interesting:" + e.message)

    try:
        return IPAddress.objects.get(pk=int(query))
    except (ObjectDoesNotExist, ValueError):
        # Check the IPAddressLog and inform the user that the IP existed at
        # sometime.
        msg = "No IP was found that matches this query: %s\n"
        try:
            if IPAddressLog.objects.filter(address=query).exists():
                msg += """However, this IP existed in the past. Check the "IP
                History" tab for more details"""
        except ObjectDoesNotExist:
            pass
        raise AdminHttp404(msg % query)


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


def get_network_details_href(ip):
    if ip.in_use():
        network = ip.nic.network
        return create_details_href('network', network.name, network.pk)
    else:
        return "-"
