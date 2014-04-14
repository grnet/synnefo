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

from synnefo.db.models import IPAddress


def get_server_ips(server, for_update=False):
    ips = IPAddress.objects.select_related("subnet")
    ips = ips.filter(nic__machine=server, deleted=False)
    if for_update:
        ips = ips.select_for_update()
    return ips


def get_server_active_ips(server, for_update=False):
    ips = get_server_ips(server, for_update=for_update)
    return ips.filter(nic__state="ACTIVE")


def get_server_public_ip(server, version=4):
    ips = get_server_active_ips(server)
    try:
        public_ips = ips.filter(network__public=True,
                                subnet__ipversion=version)
        return public_ips[0].address
    except IndexError:
        return None


def get_floating_ips(for_update=False):
    ips = IPAddress.objects.select_related("subnet")
    ips = ips.filter(floating_ip=True, deleted=False)
    if for_update:
        ips = ips.select_for_update()
    return ips


def get_server_floating_ips(server, for_update=False):
    floating_ips = get_floating_ips(for_update=for_update)
    return floating_ips.filter(nic__machine=server)


def get_server_floating_ip(server, address, for_update=False):
    server_fips = get_server_floating_ips(server, for_update=for_update)
    return server_fips.get(address=address)


def get_user_floating_ip(userid, address, for_update=False):
    fips = get_floating_ips(for_update=for_update)
    return fips.get(userid=userid, address=address)
