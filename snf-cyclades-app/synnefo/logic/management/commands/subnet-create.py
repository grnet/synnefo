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

from synnefo.management import common
from snf_django.management.commands import SynnefoCommand
from snf_django.management.utils import parse_bool
from synnefo.management import pprint
from synnefo.logic import subnets

HELP_MSG = """

Create a new subnet without authenticating the user. The limit of one
IPv4/IPv6 subnet per network still applies. Mandatory fields are CIDR and the
Network ID.
"""


class Command(SynnefoCommand):
    help = "Create a new Subnet." + HELP_MSG

    option_list = SynnefoCommand.option_list + (
        make_option("--network", dest="network_id",
                    help="Specify the Network to attach the subnet. To get the"
                         " networks of a user, use snf-manage network-list"),
        make_option("--cidr", dest="cidr",
                    help="The CIDR of the subnet, e.g., 192.168.42.0/24"),
        make_option("--allocation-pool", dest="allocation_pools",
                    action="append",
                    help="IP allocation pools to be used for assigning IPs to"
                    " VMs. Can be used multiple times. Syntax: \n"
                    "192.168.42.220,192.168.42.240. Starting IP must proceed "
                    "ending IP.20,192.168.42.240. Starting IP must proceed "
                    "ending IP. If no allocation pools are given, the whole "
                    "subnet range is used, excluding the gateway IP, the "
                    "broadcast address and the network address"),
        make_option("--name", dest="name",
                    help="An arbitrary string for naming the subnet."),
        make_option("--ip-version", dest="ipversion", choices=["4", "6"],
                    metavar="4|6",
                    help="IP version of the CIDR. The value must be in sync"
                    " with the CIDR. Default value: 4"),
        make_option("--gateway", dest="gateway",
                    help="An IP to use as a gateway for the subnet."
                    " The IP must be inside the CIDR range and cannot be the"
                    " subnet or broadcast IP. If no value is specified, a"
                    " gateway will not be set."),
        make_option("--dhcp", dest="dhcp", default="True",
                    choices=["True", "False"], metavar="True|False",
                    help="Value for DHCP/SLAAC. True by default."),
        make_option("--dns", dest="dns",
                    help="DNS nameservers to be used by the VMs in the subnet."
                    " For the time being, this option isn't supported."),
        make_option("--host-routes", dest="host_routes",
                    help="Host routes to be used for advanced routing"
                    "settings. For the time being, this option isn't"
                    " supported.")
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        network_id = options["network_id"]
        cidr = options["cidr"]

        if not network_id:
            raise CommandError("network is mandatory")
        if not cidr:
            raise CommandError("cidr is mandatory")

        user_id = common.get_resource("network", network_id).userid
        name = options["name"] or ""
        allocation_pools = options["allocation_pools"]
        ipversion = options["ipversion"] or 4
        ipversion = int(ipversion)
        gateway = options["gateway"]
        dhcp = parse_bool(options["dhcp"])
        dns = options["dns"]
        host_routes = options["host_routes"]

        alloc = None
        if allocation_pools is not None:
            alloc = subnets.parse_allocation_pools(allocation_pools)
            alloc.sort()

        sub = subnets.create_subnet(name=name,
                                    network_id=network_id,
                                    cidr=cidr,
                                    allocation_pools=alloc,
                                    gateway=gateway,
                                    ipversion=ipversion,
                                    dhcp=dhcp,
                                    slaac=dhcp,
                                    dns_nameservers=dns,
                                    host_routes=host_routes,
                                    user_id=user_id)

        pprint.pprint_subnet_in_db(sub, stdout=self.stdout)
        self.stdout.write("\n\n")
        pprint.pprint_ippool(sub, stdout=self.stdout)
