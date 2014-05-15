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

from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.management import utils

from astakos.quotaholder_app.models import Commission, Provision


class Command(SynnefoCommand):
    args = "<commission serial>"
    help = "Show details for a pending commission"

    def handle(self, *args, **options):
        self.output_format = options['output_format']

        if len(args) != 1:
            raise CommandError("Please provide a commission serial.")

        try:
            serial = int(args[0])
        except ValueError:
            raise CommandError('Expecting an integer serial.')

        try:
            commission = Commission.objects.get(serial=serial)
        except Commission.DoesNotExist:
            m = 'There is no pending commission with serial %s.' % serial
            raise CommandError(m)

        data = {'serial':     serial,
                'name':       commission.name,
                'clientkey':  commission.clientkey,
                'issue_time': commission.issue_datetime,
                }
        self.pprint_dict(data)

        provisions = Provision.objects.filter(serial=commission)
        data, labels = self.show_provisions(provisions)
        self.stdout.write('\n')
        self.pprint_table(data, labels, title='Provisions')

    def show_provisions(self, provisions):
        acc = []
        labels = 'holder', 'resource', 'source', 'quantity'
        for provision in provisions:
            fields = []
            for label in labels:
                f = getattr(provision, label)
                fields.append(f)
            acc.append(fields)
        return acc, labels

    def pprint_dict(self, d, vertical=True):
        utils.pprint_table(self.stdout, [d.values()], d.keys(),
                           self.output_format, vertical=vertical)

    def pprint_table(self, tbl, labels, title=None):
        utils.pprint_table(self.stdout, tbl, labels,
                           self.output_format, title=title)
