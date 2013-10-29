# Copyright 2012-2013 GRNET S.A. All rights reserved.
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
from synnefo.management.common import get_network

from synnefo.db.models import (Backend, pooled_rapi_client)
from synnefo.logic.rapi import GanetiApiError
from snf_django.lib.astakos import UserCache
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_BASE_URL)
from util import pool_map_chunks
from snf_django.management.utils import pprint_table
from synnefo.lib.ordereddict import OrderedDict


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

        network = get_network(args[0])

        ucache = UserCache(ASTAKOS_BASE_URL, ASTAKOS_TOKEN)

        displayname = options['displayname']

        userid = network.userid
        db_network = OrderedDict([
            ("name", network.name),
            ("backend-name", network.backend_id),
            ("state", network.state),
            ("userid", userid),
            ("username", ucache.get_name(userid) if displayname else ""),
            ("public", network.public),
            ("floating_ip_pool", network.floating_ip_pool),
            ("external_router", network.external_router),
            ("drained", network.drained),
            ("MAC prefix", network.mac_prefix),
            ("flavor", network.flavor),
            ("link", network.link),
            ("mode", network.mode),
            ("deleted", network.deleted),
            ("tags", "), ".join(network.backend_tag)),
            ("action", network.action)])

        pprint_table(self.stdout, db_network.items(), None, separator=" | ",
                     title="State of Network in DB")

        subnets = list(network.subnets.values_list("id", "name", "ipversion",
                                                   "cidr", "gateway", "dhcp",
                                                   "deleted"))
        headers = ["ID", "Name", "Version", "CIDR", "Gateway", "DHCP",
                   "Deleted"]
        write("\n\n")
        pprint_table(self.stdout, subnets, headers, separator=" | ",
                     title="Subnets")

        bnets = list(network.backend_networks.values_list(
            "backend__clustername",
            "operstate", "deleted", "backendjobid",
            "backendopcode", "backendjobstatus"))
        headers = ["Backend", "State", "Deleted", "JobID", "Opcode",
                   "JobStatus"]
        write("\n\n")
        pprint_table(self.stdout, bnets, headers, separator=" | ",
                     title="Backend Networks")

        write("\n\n")

        for backend in Backend.objects.exclude(offline=True):
            with pooled_rapi_client(backend) as client:
                try:
                    g_net = client.GetNetwork(network.backend_id)
                    ip_map = g_net.pop("map")
                    pprint_table(self.stdout, g_net.items(), None,
                                 title="State of network in backend: %s" %
                                       backend.clustername)
                    write(splitPoolMap(ip_map, 80) + "\n\n")
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
