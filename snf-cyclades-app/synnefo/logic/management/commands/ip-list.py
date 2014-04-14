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
from synnefo.db.models import IPAddressLog
from optparse import make_option

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
        make_option(
            '--active',
            dest="active",
            action="store_true",
            default=False,
            help="Display only IPs that are currently in use")
    )

    object_class = IPAddressLog
    order_by = "allocated_at"

    FIELDS = {
        "address": ("address", "The IP address"),
        "server": ("server_id", "The the server connected to"),
        "network": ("network_id", "The id of the network"),
        "allocated_at": ("allocated_at", "Datetime IP allocated to server"),
        "released_at": ("released_at", "Datetime IP released from server"),
        "active": ("active", "Whether IP still allocated to server"),
    }

    fields = ["address", "server", "network", "allocated_at", "released_at"]

    def handle_args(self, *args, **options):
        if options["address"]:
            self.filters["address"] = options["address"]
        if options["server"]:
            self.filters["server_id"] = options["server"]
        if options["active"]:
            self.filters["active"] = True
