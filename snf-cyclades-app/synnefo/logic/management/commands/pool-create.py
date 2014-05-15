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
from synnefo.db.utils import validate_mac
from synnefo.management.common import pool_table_from_type

POOL_CHOICES = ['bridge', 'mac-prefix']


class Command(SynnefoCommand):
    help = "Create a new pool of resources."
    output_transaction = True
    option_list = SynnefoCommand.option_list + (
        make_option("--type", dest="type",
                    choices=POOL_CHOICES,
                    help="Type of pool. Choices:"
                         " %s" % ",".join(POOL_CHOICES)
                    ),
        make_option("--size", dest="size",
                    help="Size of the pool"),
        make_option("--offset", dest="offset"),
        make_option("--base", dest="base")
    )

    def handle(self, *args, **options):
        type_ = options['type']
        size = options['size']
        offset = options['offset']
        base = options['base']

        if not type_:
            raise CommandError("Type of pool is mandatory")
        if not size:
            raise CommandError("Size of pool is mandatory")

        try:
            size = int(size)
        except ValueError:
            raise CommandError("Invalid size")

        if type_ == "mac-prefix":
            if base is None:
                base = "aa:00:0"
            try:
                validate_mac(base + "0:00:00:00")
            except:
                raise CommandError("Invalid base. %s is not a"
                                   " valid MAC prefix." % base)

        pool_table = pool_table_from_type(type_)

        if pool_table.objects.exists():
            raise CommandError("Pool of type %s already exists" % type_)

        pool_table.objects.create(available_map="",
                                  reserved_map="",
                                  size=size,
                                  base=base,
                                  offset=offset)
