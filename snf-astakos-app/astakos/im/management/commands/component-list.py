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

from astakos.im.models import Component
from snf_django.management.commands import ListCommand


class Command(ListCommand):
    help = "List components"
    object_class = Component

    FIELDS = {
        "id": ("id", "Component ID"),
        "name": ("name", "Component Name"),
        "base_url": ("base_url", "Component base URL"),
        "ui_url": ("url", "Component UI URL"),
        "token": ("auth_token", "Authentication token"),
        "token_created": ("auth_token_created", "Token creation date"),
    }

    fields = ["id", "name", "base_url"]
