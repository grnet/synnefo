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

import json

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from synnefo.management.common import get_network, Omit

from synnefo.db.models import (Backend, BackendNetwork,
                               pooled_rapi_client)
from synnefo.logic.rapi import GanetiApiError
from synnefo.lib.astakos import UserCache
from synnefo.settings import (CYCLADES_ASTAKOS_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_URL)
from util import pool_map_chunks


class Command(BaseCommand):
    help = "Inspect a network on DB and Ganeti."

    option_list = BaseCommand.option_list + (
        make_option(
            '--displayname',
            action='store_true',
            dest='displayname',
            default=False,
            help="Display both uuid and display name"),
    )

    def handle(self, *args, **options):
        write = self.stdout.write
        if len(args) != 1:
            raise CommandError("Please provide a network ID.")

        net = get_network(args[0])

        ucache = UserCache(ASTAKOS_URL, ASTAKOS_TOKEN)

        displayname = options['displayname']

        sep = '-' * 80 + '\n'
        labels = filter(lambda x: x is not Omit,
                        ['name', 'backend-name', 'state', 'owner uuid',
                         'owner_name' if displayname else Omit, 'subnet',
                         'gateway', 'mac_prefix', 'link', 'public', 'dhcp',
                         'flavor', 'deleted', 'action', 'pool'])

        uuid = net.userid
        if displayname:
            dname = ucache.get_name(uuid)

        fields = filter(lambda x: x is not Omit,
                        [net.name, net.backend_id, net.state, uuid or '-',
                         dname or '-' if displayname else Omit,
                         str(net.subnet), str(net.gateway),
                         str(net.mac_prefix),
                         str(net.link), str(net.public),  str(net.dhcp),
                         str(net.flavor), str(net.deleted), str(net.action),
                         str(splitPoolMap(net.get_pool().to_map(), 64))])

        write(sep)
        write('State of Network in DB\n')
        write(sep)
        for l, f in zip(labels, fields):
            write(l.ljust(20) + ': ' + f.ljust(20) + '\n')

        labels = ('Backend', 'State', 'Deleted', 'JobID', 'OpCode',
                  'JobStatus')
        for back_net in BackendNetwork.objects.filter(network=net):
            write('\n')
            fields = (back_net.backend.clustername, back_net.operstate,
                      str(back_net.deleted),  str(back_net.backendjobid),
                      str(back_net.backendopcode),
                      str(back_net.backendjobstatus))
            for l, f in zip(labels, fields):
                write(l.ljust(20) + ': ' + f.ljust(20) + '\n')
        write('\n')

        write(sep)
        write('State of Network in Ganeti\n')
        write(sep)

        for backend in Backend.objects.exclude(offline=True):
            with pooled_rapi_client(backend) as client:
                try:
                    g_net = client.GetNetwork(net.backend_id)
                    write("Backend: %s\n" % backend.clustername)
                    print json.dumps(g_net, indent=2)
                    write(sep)
                except GanetiApiError as e:
                    if e.code == 404:
                        write('Network does not exist in backend %s\n' %
                              backend.clustername)
                    else:
                        raise e


def splitPoolMap(s, count):
    chunks = pool_map_chunks(s, count)
    acc = []
    count = 0
    for chunk in chunks:
        chunk_len = len(chunk)
        acc.append(str(count).rjust(3) + ' ' + chunk + ' ' +
                   str(count + chunk_len - 1).ljust(4))
        count += chunk_len
    return '\n' + '\n'.join(acc)
