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
from snf_django.management.commands import ListCommand
from synnefo.settings import CYCLADES_SERVICE_TOKEN, ASTAKOS_AUTH_URL
from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "List Floating IPs"
    object_class = IPAddress
    select_related = ["nic"]
    deleted_field = "deleted"
    user_uuid_field = "userid"
    astakos_auth_url = ASTAKOS_AUTH_URL
    astakos_token = CYCLADES_SERVICE_TOKEN
    filters = {'floating_ip': True}

    def get_server(ip):
        try:
            return ip.nic.machine_id
        except AttributeError:
            return None

    FIELDS = {
        "id": ("id", "Floating IP UUID"),
        "user.uuid": ("userid", "The UUID of the server's owner"),
        "address": ("address", "IP Address"),
        "network": ("network_id", "Network ID"),
        "port": ("nic_id", "Port ID"),
        "server": (get_server, "Server using this Floating IP"),
        "created": ("created", "Datetime this IP was reserved"),
        "deleted": ("deleted", "If the floating IP is deleted"),
    }

    fields = ["id", "address", "network", "server", "port", "user.uuid",
              "created"]
