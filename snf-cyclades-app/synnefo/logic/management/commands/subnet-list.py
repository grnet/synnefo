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

from optparse import make_option

from snf_django.management.commands import ListCommand, CommandError
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_AUTH_URL)
from synnefo.db.models import Subnet

from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "List subnets"

    option_list = ListCommand.option_list + (
        make_option(
            "--ipv4",
            action="store_true",
            dest="ipv4",
            default=False,
            help="List only IPv4 subnets"),
        make_option(
            "--ipv6",
            action="store_true",
            dest="ipv6",
            default=False,
            help="List only IPv6 subnets"),
        make_option(
            "--dhcp",
            action="store_true",
            dest="dhcp",
            default=False,
            help="List only subnets that have DHCP/SLAC enabled"),
        make_option(
            "--public",
            action="store_true",
            dest="public",
            default=False,
            help="List only public subnets"),
    )

    object_class = Subnet
    astakos_auth_url = ASTAKOS_AUTH_URL
    astakos_token = ASTAKOS_TOKEN
    deleted_field = "deleted"

    FIELDS = {
        "id": ("id", "ID of the subnet"),
        "network": ("network_id", "ID of the network the subnet belongs to"),
        "name": ("name", "Name of the subnet"),
        "user.uuid": ("userid", "The UUID of the subnet's owner"),
        "cidr": ("cidr", "The CIDR of the subnet"),
        "ipversion": ("ipversion", "The IP version of the subnet"),
        "gateway": ("gateway", "The gateway IP of the subnet"),
        "dhcp": ("dhcp", "DHCP flag of the subnet"),
        "public": ("public", "Public flag of the subnet"),
    }

    fields = ["id", "network", "name", "user.uuid", "cidr", "ipversion",
              "gateway", "dhcp", "public"]

    def handle_args(self, *args, **options):
        if options["ipv4"] and options["ipv6"]:
            raise CommandError("Use either --ipv4 or --ipv6, not both")

        if options["ipv4"]:
            self.filters["ipversion"] = 4

        if options["ipv6"]:
            self.filters["ipversion"] = 6

        if options["dhcp"]:
            self.filters["dhcp"] = True

        if options["public"]:
            self.filters["public"] = True
