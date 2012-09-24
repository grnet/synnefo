# Copyright 2012 GRNET S.A. All rights reserved.
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

from django.core.management.base import BaseCommand, CommandError
from optparse import make_option

from util import pool_table_from_type

POOL_CHOICES = ['bridge', 'mac-prefix']


class Command(BaseCommand):
    help = "Create a new pool of resources."
    output_transaction = True
    option_list = BaseCommand.option_list + (
        make_option("--type", dest="type",
                    choices=POOL_CHOICES,
                    help="Type of pool"
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

        pool_table = pool_table_from_type(type_)

        pool_table.objects.create(available_map="",
                                  reserved_map="",
                                  size=size,
                                  base=base,
                                  offset=offset)
