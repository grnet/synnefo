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

from django.core.management.base import CommandError
from snf_django.management.commands import SynnefoCommand
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
