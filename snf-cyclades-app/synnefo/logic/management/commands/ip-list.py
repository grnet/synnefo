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


from snf_django.management.commands import ListCommand
from synnefo.db.models import IPAddressHistory
from optparse import make_option
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_AUTH_URL)

from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "Information about a floating IP"

    option_list = ListCommand.option_list + (
        make_option(
            '--address',
            dest='address',
            help="Display IP history only for this address"),
        make_option(
            '--server',
            dest='server',
            help="Display IP history only for this server"),
    )

    user_uuid_field = "user_id"
    astakos_auth_url = ASTAKOS_AUTH_URL
    astakos_token = ASTAKOS_TOKEN
    object_class = IPAddressHistory
    order_by = "action_date"

    FIELDS = {
        "address": ("address", "The IP address"),
        "user": ("user_id", "The associated user"),
        "server": ("server_id", "The server the IP is connected to"),
        "network": ("network_id", "The id of the network"),
        "action": ("action", "IP Action"),
        "date": ("action_date", "The IP action date"),
        "reason": ("action_reason", "Reason of IP action"),
    }

    fields = ["address", "user", "server", "network", "action", "date"]

    def handle_args(self, *args, **options):
        if options["address"]:
            self.filters["address"] = options["address"]
        if options["server"]:
            self.filters["server_id"] = options["server"]
