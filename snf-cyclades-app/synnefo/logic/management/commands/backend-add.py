# Copyright 2011-2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.
#
import sys
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from synnefo.db.models import Backend, Network
from django.db.utils import IntegrityError
from synnefo.logic.backend import (get_physical_resources,
                                   update_resources,
                                   create_network_synced,
                                   connect_network_synced)
from synnefo.management.common import check_backend_credentials
from synnefo.webproject.management.utils import pprint_table


HYPERVISORS = [h[0] for h in Backend.HYPERVISORS]


class Command(BaseCommand):
    can_import_settings = True

    help = 'Create a new backend.'
    option_list = BaseCommand.option_list + (
        make_option('--clustername', dest='clustername'),
        make_option('--port', dest='port', default=5080),
        make_option('--user', dest='username'),
        make_option('--pass', dest='password'),
        make_option(
            '--no-check',
            action='store_false',
            dest='check',
            default=True,
            help="Do not perform credentials check and resources update"),
        make_option(
            '--hypervisor',
            dest='hypervisor',
            default=None,
            choices=HYPERVISORS,
            metavar="|".join(HYPERVISORS),
            help="The hypervisor that the Ganeti backend uses"),
        make_option(
            '--no-init', action='store_false',
            dest='init', default=True,
            help="Do not perform initialization of the Backend Model")
    )

    def handle(self, *args, **options):
        if len(args) > 0:
            raise CommandError("Command takes no arguments")

        clustername = options['clustername']
        port = options['port']
        username = options['username']
        password = options['password']

        if not (clustername and username and password):
            raise CommandError("Clustername, user and pass must be supplied")

        # Ensure correctness of credentials
        if options['check']:
            check_backend_credentials(clustername, port, username, password)

        create_backend(clustername, port, username, password,
                       hypervisor=options["hypervisor"],
                       initialize=options["init"])


def create_backend(clustername, port, username, password, hypervisor=None,
                   initialize=True, stream=sys.stdout):
        kw = {"clustername": clustername,
              "port": port,
              "username": username,
              "password": password,
              "drained": True}

        if hypervisor:
            kw["hypervisor"] = hypervisor

        # Create the new backend in database
        try:
            backend = Backend.objects.create(**kw)
        except IntegrityError as e:
            raise CommandError("Cannot create backend: %s\n" % e)

        stream.write("Successfully created backend with id %d\n" % backend.id)

        if not initialize:
            return

        stream.write("Retrieving backend resources:\n")
        resources = get_physical_resources(backend)
        attr = ['mfree', 'mtotal', 'dfree', 'dtotal', 'pinst_cnt', 'ctotal']

        table = [[str(resources[x]) for x in attr]]
        pprint_table(stream, table, attr)

        update_resources(backend, resources)

        networks = Network.objects.filter(deleted=False, floating_ip_pool=True)
        if not networks:
            return

        stream.write("Creating the follow networks:\n")
        headers = ('Name', 'Subnet', 'Gateway', 'Mac Prefix', 'Public')
        table = []

        for net in networks:
            table.append((net.backend_id, str(net.subnet), str(net.gateway),
                         str(net.mac_prefix), str(net.public)))
        pprint_table(stream, table, headers)

        for net in networks:
            net.create_backend_network(backend)
            result = create_network_synced(net, backend)
            if result[0] != "success":
                stream.write('\nError Creating Network %s: %s\n' %
                             (net.backend_id, result[1]))
            else:
                stream.write('Successfully created Network: %s\n' %
                             net.backend_id)
            result = connect_network_synced(network=net, backend=backend)
            if result[0] != "success":
                stream.write('\nError Connecting Network %s: %s\n' %
                             (net.backend_id, result[1]))
            else:
                stream.write('Successfully connected Network: %s\n' %
                             net.backend_id)
