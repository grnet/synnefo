
# Copyright (C) 2010-2017 GRNET S.A.
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
from synnefo.db.models import RescueImage
from synnefo.api import util

from logging import getLogger


log = getLogger(__name__)


HELP_MSG = """List all rescue images"""


class Command(ListCommand):
    output_transaction = True
    help = HELP_MSG

    object_class = RescueImage
    deleted_field = "deleted"

    FIELDS = {
        "id": ("id", "ID of the image"),
        "name": ("name", "Name of the image"),
        "location_type": ("location_type", "The filetype of the image "
                                           "(e.g. http, file)"),
        "location": ("location", "The URI of the rescue image"),
        "os_family": ("os_family", "The OS family of the rescue image"),
        "os": ("os", "The Operating System of the rescue image"),
        "target_os_family": ("target_os_family", "The Target OS family "
                                                 "of the rescue image"),
        "target_os": ("target_os", "The Target Operating System of the rescue "
                                   "image"),
        "deleted": ("deleted", "Whether the image is deleted or not"),
        "is_default": ("is_default", "Whether the image is default or not"),
        "vms_using_image": ("vms_using_image", "VMs currently using this "
                                               "rescue image")
    }

    fields = ["id", "name", "location_type", "location", "os_family", "os",
              "target_os", "target_os_family", "deleted", "is_default",
              "vms_using_image"]

    def handle_db_objects(self, rows, *args, **kwargs):
        for ri in rows:
            ri.vms_using_image = len(util.get_vms_using_rescue_image(ri))
