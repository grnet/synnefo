# Copyright 2013 GRNET S.A. All rights reserved.
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
from synnefo.management import common

from synnefo.logic import subnets

HELP_MSG = """

Create a new subnet without authenticating the user. The limit of one
IPv4/IPv6 subnet per network still applies. Mandatory fields are CIDR and the
Network ID.
"""


class Command(BaseCommand):
    help = "Create a new Subnet." + HELP_MSG

    option_list = BaseCommand.option_list + (
        make_option("--network-id", dest="network_id",
                    help="Specify the Network to attach the subnet. To get the"
                         " networks of a user, use snf-manage network-list"
                         " --user ID."),
        make_option("--cidr", dest="cidr",
                    help="The CIDR of the subnet, e.g., 192.168.42.0/24"),
        make_option("--allocation-pools", dest="allocation_pools",
                    help="IP allocation pools to be used for assigning IPs to"
                    " VMs. Syntax: \n"
                    "'[[192.168.42.100,192.168.42.200],"
                    "[192.168.42.220,129.168.42.240]]'"),
        make_option("--name", dest="name",
                    help="An arbitrary string for naming the subnet."),
        make_option("--ip-version", dest="ipversion",
                    help="IP version of the CIDR. The only acceptable value"
                    " is 4 or 6. The value must also be in sync with the"
                    " CIDR. Default value: 4"),
        make_option("--gateway", dest="gateway",
                    help="An IP to use as a gateway for the subnet."
                    " The IP must be inside the CIDR range and cannot be the"
                    " subnet or broadcast IP. If no value is specified, the"
                    " first available IP of the subnet will be used."),
        make_option("--no-dhcp", action="store_true", dest="dhcp",
                    default=False,
                    help="True/False value for DHCP/SLAAC. True by default."),
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
            raise CommandError("network-id is mandatory")
        if not cidr:
            raise CommandError("cidr is mandatory")

        user_id = common.get_network(network_id).userid
        name = options["name"]
        allocation_pools = options["allocation_pools"]
        ipversion = options["ipversion"]
        if not ipversion:
            ipversion = 4
        else:
            try:
                ipversion = int(ipversion)
            except ValueError:
                raise CommandError("ip-version must be 4 or 6")

        gateway = options["gateway"]
        if not gateway:
            gateway = ""
        dhcp = options["dhcp"]
        dhcp = False if dhcp else True
        dns = options["dns"]
        host_routes = options["host_routes"]

        subnets.create_subnet(name=name,
                              network_id=network_id,
                              cidr=cidr,
                              allocation_pools=allocation_pools,
                              gateway=gateway,
                              ipversion=ipversion,
                              dhcp=dhcp,
                              slac=dhcp,
                              dns_nameservers=dns,
                              host_routes=host_routes,
                              user_id=user_id)
