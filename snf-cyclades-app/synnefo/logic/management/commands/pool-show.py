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

from django.core.management.base import CommandError
from optparse import make_option

from synnefo.db.pools import bitarray_to_map
from synnefo.management import pprint, common
from snf_django.management.commands import SynnefoCommand

POOL_CHOICES = ['bridge', 'mac-prefix']


class Command(SynnefoCommand):
    args = "<pool_id>"
    help = "Show a pool"
    output_transaction = True
    option_list = SynnefoCommand.option_list + (
        make_option('--type', dest='type',
                    choices=POOL_CHOICES,
                    help="Type of pool"
                    ),
    )

    def handle(self, *args, **options):
        type_ = options['type']

        if not type_:
            raise CommandError("Type of pool is mandatory")

        pool_table = common.pool_table_from_type(type_)

        try:
            pool_id = int(args[0])
            pool_row = pool_table.objects.get(id=pool_id)
        except IndexError:
            raise CommandError("Please provide a pool ID")
        except (ValueError, pool_table.DoesNotExist):
            raise CommandError("Invalid pool ID")

        pool = pool_row.pool

        kv = {
            'id': pool_row.id,
            'offset': pool_row.offset,
            'base': pool_row.base,
            'size': pool_row.size,
            'available': pool.count_available(),
            'reserved': pool.count_reserved(),
        }

        for key, val in sorted(kv.items()):
            line = '%s: %s\n' % (key.rjust(16), val)
            self.stdout.write(line.encode('utf8'))

        step = (type_ == 'bridge') and 64 or 80
        pprint.pprint_pool('Available', pool.to_map(), step, self.stdout)
        pprint.pprint_pool('Reserved',
                           bitarray_to_map(pool.reserved[:pool_row.size]),
                           step, self.stdout)
