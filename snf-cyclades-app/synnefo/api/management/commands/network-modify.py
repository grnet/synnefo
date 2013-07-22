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

from synnefo.db.models import Network, pooled_rapi_client
from synnefo.management.common import (validate_network_info, get_network,
                                       get_backend)
from synnefo.webproject.management.utils import parse_bool
from synnefo.logic.backend import create_network, delete_network

HELP_MSG = """Modify a network.

This management command will only modify the state of the network in Cyclades
DB. The state of the network in the Ganeti backends will remain unchanged. You
should manually modify the network in all the backends, to synchronize the
state of DB and Ganeti.

The only exception is add_reserved_ips and remove_reserved_ips options, which
modify the IP pool in the Ganeti backends.
"""


class Command(BaseCommand):
    args = "<network id>"
    help = HELP_MSG
    output_transaction = True

    option_list = BaseCommand.option_list + (
        make_option(
            '--name',
            dest='name',
            metavar='NAME',
            help="Set network's name"),
        make_option(
            '--userid',
            dest='userid',
            help="Set the userid of the network owner"),
        make_option(
            '--subnet',
            dest='subnet',
            help="Set network's subnet"),
        make_option(
            '--gateway',
            dest='gateway',
            help="Set network's gateway"),
        make_option(
            '--subnet6',
            dest='subnet6',
            help="Set network's IPv6 subnet"),
        make_option(
            '--gateway6',
            dest='gateway6',
            help="Set network's IPv6 gateway"),
        make_option(
            '--dhcp',
            dest='dhcp',
            metavar="True|False",
            choices=["True", "False"],
            help="Set if network will use nfdhcp"),
        make_option(
            '--state',
            dest='state',
            metavar='STATE',
            help="Set network's state"),
        make_option(
            '--link',
            dest='link',
            help="Set the connectivity link"),
        make_option(
            '--mac-prefix',
            dest="mac_prefix",
            help="Set the MAC prefix"),
        make_option(
            '--add-reserved-ips',
            dest="add_reserved_ips",
            help="Comma seperated list of IPs to externally reserve."),
        make_option(
            '--remove-reserved-ips',
            dest="remove_reserved_ips",
            help="Comma seperated list of IPs to externally release."),
        make_option(
            "--drained",
            dest="drained",
            metavar="True|False",
            choices=["True", "False"],
            help="Set as drained to exclude for IP allocation."
                 " Only used for public networks."),
        make_option(
            "--add-to-backend",
            dest="add_to_backend",
            help="Create a public network to a Ganeti backend."),
        make_option(
            "--remove-from-backend",
            dest="remove_from_backend",
            help="Remove a public network from a Ganeti backend."),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a network ID")

        network = get_network(args[0])

        # Validate subnet
        if options.get('subnet'):
            validate_network_info(options)

        # Validate state
        state = options.get('state')
        if state:
            allowed = [x[0] for x in Network.OPER_STATES]
            if state not in allowed:
                msg = "Invalid state, must be one of %s" % ', '.join(allowed)
                raise CommandError(msg)

        dhcp = options.get("dhcp")
        if dhcp:
            options["dhcp"] = parse_bool(dhcp)
        drained = options.get("drained")
        if drained:
            options["drained"] = parse_bool(drained)
        fields = ('name', 'userid', 'subnet', 'gateway', 'subnet6', 'gateway6',
                  'dhcp', 'state', 'link', 'mac_prefix', 'drained')
        for field in fields:
            value = options.get(field, None)
            if value is not None:
                network.__setattr__(field, value)

        network.save()

        add_reserved_ips = options.get('add_reserved_ips')
        remove_reserved_ips = options.get('remove_reserved_ips')
        if add_reserved_ips or remove_reserved_ips:
            if add_reserved_ips:
                add_reserved_ips = add_reserved_ips.split(",")
            if remove_reserved_ips:
                remove_reserved_ips = remove_reserved_ips.split(",")

            for bnetwork in network.backend_networks.all():
                with pooled_rapi_client(bnetwork.backend) as c:
                    c.ModifyNetwork(network=network.backend_id,
                                    add_reserved_ips=add_reserved_ips,
                                    remove_reserved_ips=remove_reserved_ips)

        add_to_backend = options["add_to_backend"]
        if add_to_backend is not None:
            backend = get_backend(add_to_backend)
            network.create_backend_network(backend=backend)
            create_network(network, backend, connect=True)
            msg = "Sent job to create network '%s' in backend '%s'\n"
            self.stdout.write(msg % (network, backend))

        remove_from_backend = options["remove_from_backend"]
        if remove_from_backend is not None:
            backend = get_backend(remove_from_backend)
            if network.nics.filter(machine__backend=backend,
                                   machine__deleted=False).exists():
                msg = "Can not remove. There are still connected VMs to this"\
                      " network"
                raise CommandError(msg)
            network.action = "DESTROY"
            network.save()
            delete_network(network, backend, disconnect=True)
            msg = "Sent job to delete network '%s' from backend '%s'\n"
            self.stdout.write(msg % (network, backend))
