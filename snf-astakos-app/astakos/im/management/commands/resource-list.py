# Copyright 2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

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
        "base_default": ("limit_with_unit", "Base project default quota"),
        "project_default": ("project_limit_with_unit",
                            "Project default quota"),
        "description": ("desc", "Description"),
        "api_visible": ("api_visible",
                        "Resource accessibility through the API"),
        "ui_visible": ("ui_visible",
                       "Resource accessibility through the UI"),
    }

    fields = ["id", "name", "base_default", "project_default",
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
