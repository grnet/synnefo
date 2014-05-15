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
from snf_django.management.commands import RemoveCommand
from optparse import make_option

from synnefo.management.common import pool_table_from_type

POOL_CHOICES = ['bridge', 'mac-prefix']


class Command(RemoveCommand):
    help = "Remove a pool."
    args = "<pool_id>"
    output_transaction = True
    command_option_list = RemoveCommand.command_option_list + (
        make_option("--type", dest="type",
                    choices=POOL_CHOICES,
                    help="Type of pool"
                    ),
    )

    def handle(self, *args, **options):
        type_ = options['type']

        if not type_:
            raise CommandError("Type of pool is mandatory")

        pool_table = pool_table_from_type(type_)

        force = options['force']
        self.confirm_deletion(force, "pool(s)", args)

        try:
            pool_id = int(args[0])
            pool = pool_table.objects.get(id=pool_id)
        except (ValueError, pool_table.DoesNotExist):
            raise CommandError("Invalid pool ID")

        pool.delete()
