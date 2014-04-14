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

from snf_django.management.commands import SynnefoCommand
from synnefo.management.common import pool_table_from_type

POOL_CHOICES = ['bridge', 'mac-prefix']


class Command(SynnefoCommand):
    args = "<pool_id>"
    help = "Modify a pool"
    output_transaction = True
    option_list = SynnefoCommand.option_list + (
        make_option('--type', dest='type',
                    choices=POOL_CHOICES,
                    help="Type of pool"
                    ),
        make_option('--offset', dest='offset'),
        make_option('--size', dest='size'),
        make_option('--base', dest='base'),
        make_option('--add-reserved', dest='add-reserved',
                    help="Comma-seperated list of values to reserve"),
        make_option('--remove-reserved', dest="remove-reserved",
                    help="Comma-seperated list of values to release"),
    )

    def handle(self, *args, **options):
        type_ = options['type']
        offset = options['offset']
        base = options['base']
        add_reserved = options['add-reserved']
        remove_reserved = options['remove-reserved']
        size = options['size']

        if not type_:
            raise CommandError("Type of pool is mandatory")

        pool_table = pool_table_from_type(type_)

        try:
            pool_id = int(args[0])
            pool_row = pool_table.objects.get(id=pool_id)
        except (ValueError, pool_table.DoesNotExist):
            raise CommandError("Invalid pool ID")

        pool = pool_row.pool
        if add_reserved:
            reserved = add_reserved.split(',')
            for value in reserved:
                pool.reserve(value, external=True)
        if remove_reserved:
            released = remove_reserved.split(',')
            for value in released:
                pool.put(value, external=True)
        pool.save(db=False)

        if offset:
            pool_row.offset = offset
        if base:
            pool_row.base = base

        # Save now, to avoid conflict with resizing pool.save()
        pool_row.save()

        size = options["size"]
        if size:
            try:
                size = int(size)
            except ValueError:
                raise CommandError("Invalid size")
            pool = pool_row.get_pool()
            self.resize_pool(pool, pool_row.size, size)
            pool.save()

    def resize_pool(self, pool, old_size, new_size):
        if new_size == old_size:
            return
        elif new_size > old_size:
            pool.extend(new_size - old_size)
        else:
            pool.shrink(old_size - new_size)
        pool.save()
