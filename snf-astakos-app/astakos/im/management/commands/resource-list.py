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
from astakos.im.models import Resource
from snf_django.management.commands import ListCommand
from ._common import show_resource_value, style_options, check_style


class Command(ListCommand):
    help = "List resources"
    object_class = Resource

    option_list = ListCommand.option_list + (
        make_option('--unit-style',
                    default='mb',
                    help=("Specify display unit for resource values "
                          "(one of %s); defaults to mb") % style_options),
    )

    FIELDS = {
        "id": ("id", "ID"),
        "name": ("name", "Resource Name"),
        "service_type": ("service_type", "Service type"),
        "service_origin": ("service_origin", "Service"),
        "unit": ("unit", "Unit of measurement"),
        "system_default": ("limit_with_unit", "System project default quota"),
        "project_default": ("project_limit_with_unit",
                            "Project default quota"),
        "description": ("desc", "Description"),
        "api_visible": ("api_visible",
                        "Resource accessibility through the API"),
        "ui_visible": ("ui_visible",
                       "Resource accessibility through the UI"),
    }

    fields = ["id", "name", "system_default", "project_default",
              "api_visible", "ui_visible"]

    def handle_args(self, *args, **options):
        self.unit_style = options['unit_style']
        check_style(self.unit_style)

    def handle_db_objects(self, rows, *args, **kwargs):
        for resource in rows:
            resource.limit_with_unit = show_resource_value(
                resource.uplimit, resource.name, self.unit_style)
            resource.project_limit_with_unit = show_resource_value(
                resource.project_default, resource.name, self.unit_style)
