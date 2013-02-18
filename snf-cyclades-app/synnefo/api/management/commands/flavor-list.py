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

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from synnefo.management.common import (format_bool, filter_results,
                                       pprint_table)

from synnefo.db.models import Flavor

FIELDS = Flavor._meta.get_all_field_names()


class Command(BaseCommand):
    help = "List flavors"

    option_list = BaseCommand.option_list + (
        make_option(
            '-c',
            action='store_true',
            dest='csv',
            default=False,
            help="Use pipes to separate values"),
        make_option(
            '--deleted',
            action='store_true',
            dest='deleted',
            default=False,
            help="Include deleted flavors"),
        make_option(
            '--filter-by',
            dest='filter_by',
            help="Filter results. Comma seperated list of key=val pairs"
                 " that displayed entries must satisfy. e.g."
                 " --filter-by \"cpu=1,ram!=1024\"."
                 "Available keys are: %s" % ", ".join(FIELDS))
    )

    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        if options['deleted']:
            flavors = Flavor.objects.all()
        else:
            flavors = Flavor.objects.filter(deleted=False)

        filter_by = options['filter_by']
        if filter_by:
            flavors = filter_results(flavors, filter_by)

        headers = ('id', 'name', 'cpus', 'ram', 'disk', 'template', 'deleted')
        table = []
        for flavor in flavors.order_by('id'):
            id = str(flavor.id)
            cpu = str(flavor.cpu)
            ram = str(flavor.ram)
            disk = str(flavor.disk)
            deleted = format_bool(flavor.deleted)
            fields = (id, flavor.name, cpu, ram, disk, flavor.disk_template,
                      deleted)

            table.append(fields)

        separator = " | " if options['csv'] else None
        pprint_table(self.stdout, table, headers, separator)
