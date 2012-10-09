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

from util import pool_table_from_type, pool_map_chunks
from synnefo.db.pools import bitarray_to_map

POOL_CHOICES = ['bridge', 'mac-prefix']

class Command(BaseCommand):
    args = "<pool ID>"
    help = "Show a pool"
    output_transaction = True
    option_list = BaseCommand.option_list + (
        make_option('--type', dest='type',
                    choices=POOL_CHOICES,
                    help="Type of pool"
                    ),
    )

    def handle(self, *args, **options):
        type_ = options['type']

        if not type_:
            raise CommandError("Type of pool is mandatory")

        pool_table = pool_table_from_type(type_)

        try:
            pool_id = int(args[0])
            pool_row = pool_table.objects.get(id=pool_id)
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
        print_map('Pool', pool.to_map(), step, self.stdout)
        print_map('Reserved', bitarray_to_map(pool.reserved), step, self.stdout)


def print_map(name, pool_map, step, out):
    sep = '*' * 80
    out.write(sep + "\n")
    out.write("%s: \n" % name)
    out.write(sep + "\n")
    count = 0
    for chunk in pool_map_chunks(pool_map, step):
        chunk_len = len(chunk)
        out.write(("%s " % count).rjust(4))
        out.write((chunk + " %d\n") % (count + chunk_len - 1))
        count += chunk_len
