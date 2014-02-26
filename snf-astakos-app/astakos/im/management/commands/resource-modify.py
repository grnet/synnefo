# Copyright 2013, 2014 GRNET S.A. All rights reserved.
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
from snf_django.management.commands import SynnefoCommand, CommandError

from snf_django.management import utils
from astakos.im.models import Resource
from astakos.im import register
from ._common import style_options, check_style, units


class Command(SynnefoCommand):
    args = "<resource name>"
    help = "Modify a resource's quota defaults and boolean flags."

    option_list = SynnefoCommand.option_list + (
        make_option('--base-default',
                    metavar='<limit>',
                    help="Specify default quota for base projects"),
        make_option('--project-default',
                    metavar='<limit>',
                    help="Specify default quota for non-base projects"),
        make_option('--unit-style',
                    default='mb',
                    help=("Specify display unit for resource values "
                          "(one of %s); defaults to mb") % style_options),
        make_option('--api-visible',
                    metavar='True|False',
                    help="Control visibility of this resource in the API"),
        make_option('--ui-visible',
                    metavar='True|False',
                    help="Control visibility of this resource in the UI"),
    )

    def handle(self, *args, **options):
        resource_name = args[0] if len(args) > 0 else None
        if resource_name is None:
            raise CommandError("Please provide a resource name.")
        resource = self.get_resource(resource_name)

        actions = {
            'base_default': self.change_base_default,
            'project_default': self.change_project_default,
            'api_visible': self.set_api_visible,
            'ui_visible': self.set_ui_visible,
        }

        opts = [(key, value)
                for (key, value) in options.items()
                if key in actions and value is not None]

        self.unit_style = options['unit_style']
        check_style(self.unit_style)

        for key, value in opts:
            action = actions[key]
            action(resource, value)

    def set_api_visible(self, resource, allow):
        try:
            allow = utils.parse_bool(allow)
        except ValueError:
            raise CommandError("Expecting a boolean value.")
        resource.api_visible = allow
        if not allow and resource.ui_visible:
            self.stderr.write("Also resetting 'ui_visible' for consistency.\n")
            resource.ui_visible = False
        resource.save()

    def set_ui_visible(self, resource, allow):
        try:
            allow = utils.parse_bool(allow)
        except ValueError:
            raise CommandError("Expecting a boolean value.")
        resource.ui_visible = allow
        if allow and not resource.api_visible:
            self.stderr.write("Also setting 'api_visible' for consistency.\n")
            resource.api_visible = True
        resource.save()

    def get_resource(self, resource_name):
        try:
            return Resource.objects.select_for_update().get(name=resource_name)
        except Resource.DoesNotExist:
            raise CommandError("Resource %s does not exist."
                               % resource_name)

    def change_base_default(self, resource, limit):
        limit = self.parse_limit(limit)
        register.update_base_default(resource, limit)

    def change_project_default(self, resource, limit):
        limit = self.parse_limit(limit)
        register.update_project_default(resource, limit)

    def parse_limit(self, limit):
        try:
            return units.parse(limit)
        except units.ParseError:
            m = ("Quota limit should be an integer, "
                 "optionally followed by a unit, or 'inf'.")
            raise CommandError(m)
