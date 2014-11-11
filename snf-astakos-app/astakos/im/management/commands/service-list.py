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

from astakos.im.models import Service
from snf_django.management.commands import ListCommand


class Command(ListCommand):
    help = "List services"
    object_class = Service

    FIELDS = {
        "id": ("id", "Service ID"),
        "name": ("name", "Service Name"),
        "component": ("component.name", "Service url"),
        "type": ("type", "Service type"),
    }

    fields = ["id", "name", "component", "type"]
