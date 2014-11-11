# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from optparse import make_option

from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from synnefo.management.common import convert_api_faults
from snf_django.management.utils import parse_bool

from synnefo.db.models import Network
from synnefo.logic import networks, subnets
from synnefo.management import pprint


NETWORK_FLAVORS = Network.FLAVORS.keys()


class Command(SynnefoCommand):
    can_import_settings = True
    output_transaction = True

    help = "Create a new network"

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--name',
            dest='name',
            help="Name of the network"),
        make_option(
            '--user',
            dest='user',
            help="The owner of the network"),
        make_option(
            '--subnet',
            dest='subnet',
            default=None,
            # required=True,
            help='IPv4 subnet of the network'),
        make_option(
            '--gateway',
            dest='gateway',
            default=None,
            help='IPv4 gateway of the network'),
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
            default="False",
            choices=["True", "False"],
            metavar="True|False",
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
            '--floating-ip-pool',
            dest='floating_ip_pool',
            default="False",
            choices=["True", "False"],
            metavar="True|False",
            help="Use the network as a Floating IP pool."),
        make_option(
            '--allocation-pool',
            dest='allocation_pools',
            action='append',
            help="IP allocation pools to be used for assigning IPs to"
                 " VMs. Can be used multiple times. Syntax: \n"
                 "192.168.42.220,192.168.42.240. Starting IP must proceed "
                 "ending IP. If no allocation pools are given, the whole "
                 "subnet range is used, excluding the gateway IP, the "
                 "broadcast address and the network address"),
        make_option(
            "--drained",
            dest="drained",
            metavar="True|False",
            choices=["True", "False"],
            default="False",
            help="Set network as drained to prevent creation of new ports."),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        name = options['name']
        subnet = options['subnet']
        gateway = options['gateway']
        subnet6 = options['subnet6']
        gateway6 = options['gateway6']
        public = options['public']
        flavor = options['flavor']
        mode = options['mode']
        link = options['link']
        mac_prefix = options['mac_prefix']
        tags = options['tags']
        userid = options["user"]
        allocation_pools = options["allocation_pools"]
        floating_ip_pool = parse_bool(options["floating_ip_pool"])
        dhcp = parse_bool(options["dhcp"])
        drained = parse_bool(options["drained"])

        if name is None:
            name = ""
        if flavor is None:
            raise CommandError("flavor is required")

        if ((subnet is None) and (subnet6 is None)) and dhcp is not False:
            raise CommandError("Cannot set DHCP without subnet or subnet6")

        if subnet is None and gateway is not None:
            raise CommandError("Cannot use gateway without subnet")
        if subnet is None and allocation_pools is not None:
            raise CommandError("Cannot use allocation-pools without subnet")
        if subnet6 is None and gateway6 is not None:
            raise CommandError("Cannot use gateway6 without subnet6")
        if flavor == "IP_LESS_ROUTED" and not (subnet or subnet6):
            raise CommandError("Cannot create 'IP_LESS_ROUTED' network without"
                               " subnet")

        if not (userid or public):
            raise CommandError("'user' is required for private networks")

        network = networks.create(userid=userid, name=name, flavor=flavor,
                                  public=public, mode=mode,
                                  link=link, mac_prefix=mac_prefix, tags=tags,
                                  floating_ip_pool=floating_ip_pool,
                                  drained=drained)

        if subnet is not None:
            alloc = None
            if allocation_pools is not None:
                alloc = subnets.parse_allocation_pools(allocation_pools)
                alloc.sort()
            name = "IPv4 Subnet of Network %s" % network.id
            subnets.create_subnet(network.id, cidr=subnet, name=name,
                                  ipversion=4, gateway=gateway, dhcp=dhcp,
                                  user_id=userid,
                                  allocation_pools=alloc)

        if subnet6 is not None:
            name = "IPv6 Subnet of Network %s" % network.id
            subnets.create_subnet(network.id, cidr=subnet6, name=name,
                                  ipversion=6, gateway=gateway6,
                                  dhcp=dhcp, user_id=userid)

        self.stdout.write("Created network '%s' in DB:\n" % network)
        pprint.pprint_network(network, stdout=self.stdout)
        pprint.pprint_network_subnets(network, stdout=self.stdout)

        networks.create_network_in_backends(network)
        # TODO: Add --wait option to track job progress and report successful
        # creation in each backend.
        self.stdout.write("\nSuccessfully issued job to create network in"
                          " backends\n")
