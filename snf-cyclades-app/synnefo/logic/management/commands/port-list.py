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

from snf_django.management.commands import ListCommand
from synnefo.db.models import NetworkInterface
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_AUTH_URL)

from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "List ports"

    option_list = ListCommand.option_list + (
        make_option(
            '--public',
            dest='public',
            action='store_true',
            default=False,
            help="List only ports connected to public networks"),
        make_option(
            '--server',
            dest='server_id',
            default=False,
            help="List ports connected to specific server"),
    )

    object_class = NetworkInterface
    user_uuid_field = "userid"
    astakos_auth_url = ASTAKOS_AUTH_URL
    astakos_token = ASTAKOS_TOKEN
    prefetch_related = ["ips"]

    def get_fixed_ips(port):
        return ",".join(port.ips.values_list("address", flat=True))

    FIELDS = {
        "id": ("id", "The ID of the port"),
        "name": ("name", "The name of the port"),
        "user.uuid": ("userid", "The UUID of the port's owner"),
        "mac_address": ("mac", "The MAC address of the port"),
        "server_id": ("machine_id", "The vm's id the port is conncted to"),
        "state": ("state", "The port's status"),
        "device_owner": ("device_owner", "The owner of the port (vm/router)"),
        "network": ("network_id", "The network's ID the port is\
                        connected to"),
        "created": ("created", "The date the port was created"),
        "updated": ("updated", "The date the port was updated"),
        "fixed_ips": (get_fixed_ips, "The ips and subnets associated with\
                                     the port"),
    }

    fields = ["id", "name", "user.uuid", "mac_address", "network",
              "server_id", "fixed_ips", "state"]

    def handle_args(self, *args, **options):
        if options["public"]:
            self.filters["network__public"] = True

        if options["server_id"]:
            self.filters["machine"] = options["server_id"]
