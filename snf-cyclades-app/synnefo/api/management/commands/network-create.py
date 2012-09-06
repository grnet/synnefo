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

from synnefo.db.models import Network, Backend
from synnefo.api.util import network_link_from_type, validate_network_size
from synnefo.logic.backend import create_network
from synnefo import settings

import ipaddr

NETWORK_TYPES = ['PUBLIC_ROUTED', 'PRIVATE_MAC_FILTERED',
                 'PRIVATE_PHYSICAL_VLAN', 'CUSTOM_ROUTED',
                 'CUSTOM_BRIDGED']


class Command(BaseCommand):
    can_import_settings = True

    help = "Create a new network"

    option_list = BaseCommand.option_list + (
        make_option('--name',
            dest='name',
            help="Name of network"),
        make_option('--owner',
            dest='owner',
            help="The owner of the network"),
        make_option('--subnet',
            dest='subnet',
            default=None,
            # required=True,
            help='Subnet of the network'),
        make_option('--gateway',
            dest='gateway',
            default=None,
            help='Gateway of the network'),
        make_option('--dhcp',
            dest='dhcp',
            action='store_true',
            default=False,
            help='Automatically assign IPs'),
        make_option('--public',
            dest='public',
            action='store_true',
            default=False,
            help='Network is public'),
        make_option('--type',
            dest='type',
            default='PRIVATE_MAC_FILTERED',
            choices=NETWORK_TYPES,
            help='Type of network. Choices: ' + ', '.join(NETWORK_TYPES)),
        make_option('--subnet6',
            dest='subnet6',
            default=None,
            help='IPv6 subnet of the network'),
        make_option('--gateway6',
            dest='gateway6',
            default=None,
            help='IPv6 gateway of the network'),
        make_option('--backend-id',
            dest='backend_id',
            default=None,
            help='ID of the backend that the network will be created. Only for'
                 ' public networks')
        )

    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        name = options['name']
        subnet = options['subnet']
        typ = options['type']
        backend_id = options['backend_id']
        public = options['public']

        if not name:
            raise CommandError("Name is required")
        if not subnet:
            raise CommandError("Subnet is required")
        if public and not backend_id:
            raise CommandError("backend-id is required")
        if backend_id and not public:
            raise CommandError("Private networks must be created to"
                               " all backends")

        if backend_id:
            try:
                backend_id = int(backend_id)
                backend = Backend.objects.get(id=backend_id)
            except ValueError:
                raise CommandError("Invalid backend ID")
            except Backend.DoesNotExist:
                raise CommandError("Backend not found in DB")

        link = network_link_from_type(typ)

        subnet, gateway, subnet6, gateway6 = validate_network_info(options)

        if not link:
            raise CommandError("Can not create network. No connectivity link")

        network = Network.objects.create(
                name=name,
                userid=options['owner'],
                subnet=subnet,
                gateway=gateway,
                dhcp=options['dhcp'],
                type=options['type'],
                public=public,
                link=link,
                gateway6=gateway6,
                subnet6=subnet6,
                state='PENDING')

        if public:
            # Create BackendNetwork only to the specified Backend
            network.create_backend_network(backend)
            create_network(network, backends=[backend])
        else:
            # Create BackendNetwork entries for all Backends
            network.create_backend_network()
            create_network(network)


def validate_network_info(options):
    subnet = options['subnet']
    gateway = options['gateway']
    subnet6 = options['subnet6']
    gateway6 = options['gateway6']

    try:
        net = ipaddr.IPv4Network(subnet)
        prefix = net.prefixlen
        if not validate_network_size(prefix):
            raise CommandError("Unsupport network mask %d."
                               " Must be in range (%s,29] "
                               % (prefix, settings.MAX_CIDR_BLOCK))
    except ValueError:
        raise CommandError('Malformed subnet')
    try:
        gateway and ipaddr.IPv4Address(gateway) or None
    except ValueError:
        raise CommandError('Malformed gateway')

    try:
        subnet6 and ipaddr.IPv6Network(subnet6) or None
    except ValueError:
        raise CommandError('Malformed subnet6')

    try:
        gateway6 and ipaddr.IPv6Address(gateway6) or None
    except ValueError:
        raise CommandError('Malformed gateway6')

    return subnet, gateway, subnet6, gateway6
