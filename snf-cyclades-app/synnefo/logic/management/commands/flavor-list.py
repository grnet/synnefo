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
from synnefo.db.models import Flavor, VirtualMachine


class Command(ListCommand):
    help = "List available server flavors"

    object_class = Flavor
    deleted_field = "deleted"
    select_related = ("volume_type", )

    def get_vms(flavor):
        return VirtualMachine.objects.filter(flavor=flavor, deleted=False)\
                                     .count()

    FIELDS = {
        "id": ("id", "Flavor's unique ID"),
        "name": ("name", "Flavor's unique name"),
        "cpu": ("cpu", "Number of CPUs"),
        "ram": ("ram", "Size(MB) of RAM"),
        "disk": ("disk", "Size(GB) of disk"),
        "volume_type": ("volume_type_id", "Volume Type ID"),
        "template": ("volume_type.disk_template", "Disk template"),
        "allow_create": ("allow_create", "Whether servers can be created from"
                                         " this flavor"),
        "vms": (get_vms, "Number of active servers using this flavor")
    }

    fields = ["id", "name", "cpu", "ram", "disk", "template", "volume_type",
              "allow_create", "vms"]
