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

#from optparse import make_option

from snf_django.management.commands import ListCommand
from synnefo.db.models import Volume
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_AUTH_URL)
from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "List Volumes"

    option_list = ListCommand.option_list

    object_class = Volume
    deleted_field = "deleted"
    user_uuid_field = "userid"
    astakos_auth_url = ASTAKOS_AUTH_URL
    astakos_token = ASTAKOS_TOKEN
    select_related = ["volume_type"]

    FIELDS = {
        "id": ("id", "ID of the server"),
        "name": ("name", "Name of the server"),
        "user.uuid": ("userid", "The UUID of the server's owner"),
        "size": ("size", "The size of the volume (GB)"),
        "server_id": ("machine_id", "The UUID of the server that the volume"
                                    " is currently attached"),
        "source": ("source", "The source of the volume"),
        "status": ("status", "The status of the volume"),
        "created": ("created", "The date the server was created"),
        "deleted": ("deleted", "Whether the server is deleted or not"),
        "volume_type": ("volume_type", "ID of volume's type"),
        "disk_template": ("volume_type.disk_template",
                          "The disk template of the volume")
    }

    fields = ["id", "user.uuid", "size", "status", "source", "disk_template",
              "volume_type", "server_id"]
