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

from astakos.im.models import Service, EndpointData
from synnefo.lib.ordereddict import OrderedDict
from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.management import utils


class Command(SynnefoCommand):
    args = "<service name or ID>"
    help = "Show service details"

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a service name or ID.")

        identifier = args[0]
        if identifier.isdigit():
            try:
                service = Service.objects.get(id=int(identifier))
            except Service.DoesNotExist:
                raise CommandError('No service found with ID %s.' % identifier)
        else:
            try:
                service = Service.objects.get(name=identifier)
            except Service.DoesNotExist:
                raise CommandError('No service found named %s.' % identifier)

        kv = OrderedDict(
            [
                ('id', service.id),
                ('name', service.name),
                ('component', service.component),
                ('type', service.type),
            ])

        utils.pprint_table(self.stdout, [kv.values()], kv.keys(),
                           options["output_format"], vertical=True)

        self.stdout.write('\n')
        endpoint_data = EndpointData.objects.filter(endpoint__service=service)
        data = []
        for ed in endpoint_data:
            data.append((ed.endpoint_id, ed.key, ed.value))

        labels = ('endpoint', 'key', 'value')
        utils.pprint_table(self.stdout, data, labels,
                           options["output_format"],
                           title='Endpoints')
