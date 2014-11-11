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
from snf_django.management.commands import SynnefoCommand
from synnefo.management.common import pool_table_from_type

POOL_CHOICES = ['bridge', 'mac-prefix']


class Command(SynnefoCommand):
    help = "List available pools"
    output_transaction = True
    option_list = SynnefoCommand.option_list + (
        make_option('--type', dest='type',
                    choices=POOL_CHOICES,
                    help="Type of pool"
                    ),
    )

    def handle(self, *args, **options):
        type_ = options['type']

        if type_:
            pool_tables = [pool_table_from_type(type_)]
        else:
            pool_tables = [pool_table_from_type(x) for x in POOL_CHOICES]

        for pool_table in pool_tables:
            self.stdout.write("-" * 80 + '\n')
            pl = pool_table.__name__.replace("Table", "")
            self.stdout.write(pl + '\n')
            self.stdout.write("-" * 80 + '\n')
            keys = ["id", "size", "base", "offset", "available", "reserved"]
            for key in keys:
                self.stdout.write(("%s" % key).rjust(12))
            self.stdout.write("\n")
            for pool_table_row in pool_table.objects.all():
                pool = pool_table_row.pool

                kv = {
                    'id': pool_table_row.id,
                    'offset': pool_table_row.offset,
                    'base': pool_table_row.base,
                    'size': pool_table_row.size,
                    'available': pool.count_available(),
                    'reserved': pool.count_reserved(),
                }

                for key in keys:
                    self.stdout.write(("%s" % kv[key]).rjust(12))
                self.stdout.write("\n")
