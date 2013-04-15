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
from synnefo.management.common import validate_network_info, get_backend
from synnefo.webproject.management.utils import pprint_table

from synnefo.db.models import Network
from synnefo.logic.backend import create_network
from synnefo.api.util import values_from_flavor

NETWORK_FLAVORS = Network.FLAVORS.keys()


class Command(BaseCommand):
    can_import_settings = True
    output_transaction = True

    help = "Create a new network"

    option_list = BaseCommand.option_list + (
        make_option(
            "-n",
            "--dry-run",
            dest="dry_run",
            default=False,
            action="store_true"),
        make_option(
            '--name',
            dest='name',
            help="Name of network"),
        make_option(
            '--owner',
            dest='owner',
            help="The owner of the network"),
        make_option(
            '--subnet',
            dest='subnet',
            default=None,
            # required=True,
            help='Subnet of the network'),
        make_option(
            '--gateway',
            dest='gateway',
            default=None,
            help='Gateway of the network'),
        make_option(
            '--subnet6',
            dest='subnet6',
            default=None,
            help='IPv6 subnet of the network'),
        make_option(
            '--gateway6',
            dest='gateway6',
            default=None,
            help='IPv6 gateway of the network'),
        make_option(
            '--dhcp',
            dest='dhcp',
            action='store_true',
            default=False,
            help='Automatically assign IPs'),
        make_option(
            '--public',
            dest='public',
            action='store_true',
            default=False,
            help='Network is public'),
        make_option(
            '--flavor',
            dest='flavor',
            default=None,
            choices=NETWORK_FLAVORS,
            help='Network flavor. Choices: ' + ', '.join(NETWORK_FLAVORS)),
        make_option(
            '--mode',
            dest='mode',
            default=None,
            help="Overwrite flavor connectivity mode."),
        make_option(
            '--link',
            dest='link',
            default=None,
            help="Overwrite flavor connectivity link."),
        make_option(
            '--mac-prefix',
            dest='mac_prefix',
            default=None,
            help="Overwrite flavor connectivity MAC prefix"),
        make_option(
            '--tags',
            dest='tags',
            default=None,
            help='The tags of the Network (comma separated strings)'),
        make_option(
            '--backend-id',
            dest='backend_id',
            default=None,
            help='ID of the backend that the network will be created. Only for'
                 ' public networks'),
    )

    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        dry_run = options["dry_run"]
        name = options['name']
        subnet = options['subnet']
        backend_id = options['backend_id']
        public = options['public']
        flavor = options['flavor']
        mode = options['mode']
        link = options['link']
        mac_prefix = options['mac_prefix']
        tags = options['tags']

        if not name:
            raise CommandError("Name is required")
        if not subnet:
            raise CommandError("Subnet is required")
        if not flavor:
            raise CommandError("Flavor is required")
        if public and not backend_id:
            raise CommandError("backend-id is required")
        if backend_id and not public:
            raise CommandError("Private networks must be created to"
                               " all backends")

        if mac_prefix and flavor == "MAC_FILTERED":
            raise CommandError("Can not override MAC_FILTERED mac-prefix")
        if link and flavor == "PHYSICAL_VLAN":
            raise CommandError("Can not override PHYSICAL_VLAN link")

        if backend_id:
            backend = get_backend(backend_id)

        fmode, flink, fmac_prefix, ftags = values_from_flavor(flavor)
        mode = mode or fmode
        link = link or flink
        mac_prefix = mac_prefix or fmac_prefix
        tags = tags or ftags

        subnet, gateway, subnet6, gateway6 = validate_network_info(options)

        if not link or not mode:
            raise CommandError("Can not create network."
                               " No connectivity link or mode")
        netinfo = {
           "name": name,
           "userid": options["owner"],
           "subnet": subnet,
           "gateway": gateway,
           "gateway6": gateway6,
           "subnet6": subnet6,
           "dhcp": options["dhcp"],
           "flavor": flavor,
           "public": public,
           "mode": mode,
           "link": link,
           "mac_prefix": mac_prefix,
           "tags": tags,
           "state": "PENDING"}

        if dry_run:
            self.stdout.write("Creating network:\n")
            pprint_table(self.stdout, tuple(netinfo.items()))
            return

        network = Network.objects.create(**netinfo)

        if public:
            # Create BackendNetwork only to the specified Backend
            network.create_backend_network(backend)
            create_network(network, backends=[backend])
        else:
            # Create BackendNetwork entries for all Backends
            network.create_backend_network()
            create_network(network)
