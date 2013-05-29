# Copyright 2013 GRNET S.A. All rights reserved.
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
from django.core.management.base import BaseCommand, CommandError
from django.utils import simplejson as json

from synnefo.webproject.management import utils
from astakos.im.models import Resource
from astakos.im.resources import update_resource
from ._common import show_resource_value, style_options, check_style, units


class Command(BaseCommand):
    args = "<resource name>"
    help = "Modify a resource's default base quota and boolean flags."

    option_list = BaseCommand.option_list + (
        make_option('--limit',
                    help="Specify default base quota"),
        make_option('--limit-interactive',
                    action='store_true',
                    default=None,
                    help=("Prompt user to change default base quota. "
                          "If no resource is given, prompts for all "
                          "resources.")),
        make_option('--limit-from-file',
                    metavar='<limits_file.json>',
                    help=("Read default base quota from a file. "
                          "File should contain a json dict mapping resource "
                          "names to limits")),
        make_option('--unit-style',
                    default='mb',
                    help=("Specify display unit for resource values "
                          "(one of %s); defaults to mb") % style_options),
        make_option('--allow-in-projects',
                    metavar='True|False',
                    help=("Specify whether to allow this resource "
                          "in projects.")),
    )

    def handle(self, *args, **options):
        resource_name = args[0] if len(args) > 0 else None

        actions = {
            'limit': self.change_limit,
            'limit_interactive': self.change_interactive,
            'limit_from_file': self.change_from_file,
            'allow_in_projects': self.set_allow_in_projects,
        }

        opts = [(key, value)
                for (key, value) in options.items()
                if key in actions and value is not None]

        if len(opts) != 1:
            raise CommandError("Please provide exactly one of the options: "
                               "--limit, --limit-interactive, "
                               "--limit-from-file, --allow-in-projects.")

        self.unit_style = options['unit_style']
        check_style(self.unit_style)

        key, value = opts[0]
        action = actions[key]
        action(resource_name, value)

    def set_allow_in_projects(self, resource_name, allow):
        if resource_name is None:
            raise CommandError("Please provide a resource name.")

        try:
            allow = utils.parse_bool(allow)
        except ValueError:
            raise CommandError("Expecting a boolean value.")
        resource = self.get_resource(resource_name)
        resource.allow_in_projects = allow
        resource.save()

    def get_resource(self, resource_name):
        try:
            return Resource.objects.get_for_update(name=resource_name)
        except Resource.DoesNotExist:
            raise CommandError("Resource %s does not exist."
                               % resource_name)

    def change_limit(self, resource_name, limit):
        if resource_name is None:
            raise CommandError("Please provide a resource name.")

        resource = self.get_resource(resource_name)
        self.change_resource_limit(resource, limit)

    def change_from_file(self, resource_name, filename):
        with open(filename) as file_data:
            try:
                config = json.load(file_data)
            except json.JSONDecodeError:
                raise CommandError("Malformed JSON file.")
            if not isinstance(config, dict):
                raise CommandError("Malformed JSON file.")
            self.change_with_conf(resource_name, config)

    def change_with_conf(self, resource_name, config):
        if resource_name is None:
            resources = Resource.objects.all().select_for_update()
        else:
            resources = [self.get_resource(resource_name)]

        for resource in resources:
            limit = config.get(resource.name)
            if limit is not None:
                self.change_resource_limit(resource, limit)

    def change_interactive(self, resource_name, _placeholder):
        if resource_name is None:
            resources = Resource.objects.all().select_for_update()
        else:
            resources = [self.get_resource(resource_name)]

        for resource in resources:
            self.stdout.write("Resource '%s' (%s)\n" %
                              (resource.name, resource.desc))
            value = show_resource_value(resource.uplimit, resource.name,
                                        self.unit_style)
            self.stdout.write("Current limit: %s\n" % value)
            while True:
                self.stdout.write("New limit (leave blank to keep current): ")
                response = raw_input()
                if response == "":
                    break
                else:
                    try:
                        value = units.parse(response)
                    except units.ParseError:
                        continue
                    update_resource(resource, value)
                    break

    def change_resource_limit(self, resource, limit):
        if not isinstance(limit, (int, long)):
            try:
                limit = units.parse(limit)
            except units.ParseError:
                m = ("Limit should be an integer, optionally followed "
                     "by a unit.")
                raise CommandError(m)
            update_resource(resource, limit)
