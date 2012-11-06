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

from synnefo.db.models import Network

from ._common import format_bool


class Command(BaseCommand):
    help = "List networks"

    option_list = BaseCommand.option_list + (
        make_option('-c',
            action='store_true',
            dest='csv',
            default=False,
            help="Use pipes to separate values"),
        make_option('--deleted',
            action='store_true',
            dest='deleted',
            default=False,
            help="List only deleted networks"),
        make_option('--public',
            action='store_true',
            dest='public',
            default=False,
            help="List only public networks"),
        make_option('--ipv6',
            action='store_true',
            dest='ipv6',
            default=False,
            help="Show IPv6 information of the network"),
        )

    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        networks = Network.objects.all()
        if options['deleted']:
            networks = networks.filter(deleted=True)
        else:
            networks = networks.exclude(deleted=True)

        if options['public']:
            networks = networks.filter(public=True)

        labels = ['id', 'name', 'type', 'owner',
                  'mac_prefix', 'dhcp', 'state', 'link', 'vms', 'public']
        columns = [3, 16, 22, 30, 10, 6, 8, 12, 4, 6]

        if options['ipv6']:
            labels.extend(['IPv6 Subnet', 'IPv6 Gateway'])
            columns.extend([16, 16])
        else:
            labels.extend(['IPv4 Subnet', 'IPv4 Gateway'])
            columns.extend([14, 14])

        if not options['csv']:
            line = ' '.join(l.rjust(w) for l, w in zip(labels, columns))
            self.stdout.write(line + '\n')
            sep = '-' * len(line)
            self.stdout.write(sep + '\n')

        for network in networks.order_by("id"):
            fields = [str(network.id),
                      network.name,
                      network.type,
                      network.userid or '',
                      network.mac_prefix or '',
                      str(network.dhcp),
                      network.state,
                      network.link or '',
                      str(network.machines.count()),
                      format_bool(network.public)]

            if options['ipv6']:
                fields.extend([network.subnet6 or '', network.gateway6 or ''])
            else:
                fields.extend([network.subnet, network.gateway or ''])

            if options['csv']:
                line = '|'.join(fields)
            else:
                line = ' '.join(f.rjust(w) for f, w in zip(fields, columns))

            self.stdout.write(line.encode('utf8') + '\n')
