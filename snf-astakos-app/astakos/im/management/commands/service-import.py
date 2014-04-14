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

from django.db import transaction
from snf_django.management.commands import SynnefoCommand, CommandError
from django.utils import simplejson as json

from astakos.im.register import add_service, add_resource, RegisterException
from astakos.im.models import Component
from ._common import read_from_file


class Command(SynnefoCommand):
    help = "Register services"

    option_list = SynnefoCommand.option_list + (
        make_option('--json',
                    dest='json',
                    metavar='<json.file>',
                    help="Load service definitions from a json file"),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):

        json_file = options['json']
        if not json_file:
            m = "Expecting option --json."
            raise CommandError(m)

        else:
            data = read_from_file(json_file)
            m = ('Input should be a JSON dict mapping service names '
                 'to definitions.')
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise CommandError(m)
            if not isinstance(data, dict):
                raise CommandError(m)
        self.add_services(data)

    def add_services(self, data):
        write = self.stderr.write
        output = []
        for name, service_dict in data.iteritems():
            try:
                component_name = service_dict['component']
                service_type = service_dict['type']
                endpoints = service_dict['endpoints']
            except KeyError:
                raise CommandError('Malformed service definition.')

            try:
                component = Component.objects.get(name=component_name)
            except Component.DoesNotExist:
                m = "Component '%s' is not registered." % component_name
                raise CommandError(m)

            try:
                existed = add_service(component, name, service_type, endpoints,
                                      out=self.stderr)
            except RegisterException as e:
                raise CommandError(e.message)

            m = "%s service %s.\n" % ("Updated" if existed else "Added", name)
            output.append(m)

            resources = service_dict.get('resources', {}).values()
            for resource in resources:
                if not isinstance(resource, dict):
                    raise CommandError("Malformed resource dict.")

                service_origin = resource.get('service_origin')
                if name != service_origin:
                    raise CommandError("service_origin mismatch.")
                try:
                    r, exists = add_resource(resource)
                except RegisterException as e:
                    raise CommandError(e.message)
                if exists:
                    m = "Resource '%s' updated in database.\n" % (r.name)
                else:
                    m = ("Resource '%s' created in database with unlimited "
                         "quota.\n" % (r.name))
                output.append(m)

        for line in output:
            write(line)
