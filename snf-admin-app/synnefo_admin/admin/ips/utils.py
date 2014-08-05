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

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from astakos.im.models import AstakosUser
from synnefo.db.models import IPAddress, IPAddressLog

from synnefo_admin.admin.exceptions import AdminHttp404
from synnefo_admin.admin.utils import create_details_href


def get_ip_or_404(query):
    try:
        return IPAddress.objects.get(address=query)
    except ObjectDoesNotExist:
        pass
    except MultipleObjectsReturned:
        raise AdminHttp404("""Hm, that's interesting. There are more than one
                           entries for this address: %s""" % query)

    try:
        return IPAddress.objects.get(pk=int(query))
    except (ObjectDoesNotExist, ValueError):
        # Check the IPAddressLog and inform the user that the IP existed at
        # sometime.
        msg = "No IP was found that matches this query: %s" % query
        try:
            if IPAddressLog.objects.filter(address=query).exists():
                msg = """This IP was deleted. Check the "IP History" tab for
                more details."""
        except ObjectDoesNotExist:
            pass
        raise AdminHttp404(msg)


def get_contact_email(inst):
    if inst.userid:
        return AstakosUser.objects.get(uuid=inst.userid).email


def get_contact_name(inst):
    if inst.userid:
        return AstakosUser.objects.get(uuid=inst.userid).realname


def get_user_details_href(ip):
    if ip.userid:
        user = AstakosUser.objects.get(uuid=ip.userid)
        return create_details_href('user', user.realname, user.email)
    else:
        return "-"


def get_vm_details_href(ip):
    if ip.in_use():
        vm = ip.nic.machine
        return create_details_href('vm', vm.name, vm.pk)
    else:
        return "-"


def get_network_details_href(ip):
    if ip.in_use():
        network = ip.nic.network
        return create_details_href('network', network.name, network.pk)
    else:
        return "-"
