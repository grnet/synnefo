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

from synnefo.api import util
from synnefo.management import common, pprint
from snf_django.management.utils import parse_bool
from snf_django.management.commands import SynnefoCommand
from synnefo.logic import servers

HELP_MSG = """Create a new port.

Connect a server/router to a network by creating a new port. If 'floating_ip'
option is used, the specified floating IP will be assigned to the new port.
Otherwise, the port will get an IP address for each Subnet that is associated
with the network."""


class Command(SynnefoCommand):
    help = HELP_MSG

    option_list = SynnefoCommand.option_list + (
        make_option(
            "--name",
            dest="name",
            default=None,
            help="Name of the port."),
        make_option(
            "--user",
            dest="user_id",
            default=None,
            help="UUID of the owner of the Port."),
        make_option(
            "--network",
            dest="network_id",
            default=None,
            help="The ID of the network where the port will be created."),
        make_option(
            "--server",
            dest="server_id",
            default=None,
            help="The ID of the server that the port will be connected to."),
        #make_option(
        #    "--router",
        #    dest="router_id",
        #    default=None,
        #    help="The ID of the router that the port will be connected to."),
        make_option(
            "--floating-ip",
            dest="floating_ip_id",
            default=None,
            help="The ID of the floating IP to use for the port."),
        make_option(
            "--ipv4-address",
            dest="ipv4_address",
            default=None,
            help="Specify IPv4 address for the new port."),
        make_option(
            "--security-groups",
            dest="security-groups",
            default=None,
            help="Comma separated list of Security Group IDs to associate"
                 " with the port."),
        make_option(
            "--wait",
            dest="wait",
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Wait for Ganeti jobs to complete. [Default: True]"),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        name = options["name"]
        user_id = options["user_id"]
        network_id = options["network_id"]
        server_id = options["server_id"]
        #router_id = options["router_id"]
        router_id = None
        # assume giving security groups comma separated
        security_group_ids = options["security-groups"]
        wait = parse_bool(options["wait"])

        if not name:
            name = ""

        if not network_id:
            raise CommandError("Please specify a 'network'")

        vm = None
        owner = None
        if server_id:
            owner = "vm"
            vm = common.get_resource("server", server_id, for_update=True)
            #if vm.router:
            #    raise CommandError("Server '%s' does not exist." % server_id)
        elif router_id:
            owner = "router"
            vm = common.get_resource("server", router_id, for_update=True)
            if not vm.router:
                raise CommandError("Router '%s' does not exist." % router_id)

        if user_id is None:
            if vm is not None:
                user_id = vm.userid
            else:
                raise CommandError("Please specify the owner of the port.")

        # get the network
        network = common.get_resource("network", network_id)

        # Get either floating IP or fixed ip address
        ipaddress = None
        floating_ip_id = options["floating_ip_id"]
        ipv4_address = options["ipv4_address"]
        if floating_ip_id:
            ipaddress = common.get_resource("floating-ip", floating_ip_id,
                                            for_update=True)
            if ipv4_address is not None and ipaddress.address != ipv4_address:
                raise CommandError("Floating IP address '%s' is different from"
                                   " specified address '%s'" %
                                   (ipaddress.address, ipv4_address))

        # validate security groups
        sg_list = []
        if security_group_ids:
            security_group_ids = security_group_ids.split(",")
            for gid in security_group_ids:
                sg = util.get_security_group(int(gid))
                sg_list.append(sg)

        new_port = servers.create_port(user_id, network, machine=vm,
                                       name=name,
                                       use_ipaddress=ipaddress,
                                       address=ipv4_address,
                                       security_groups=sg_list,
                                       device_owner=owner)
        self.stdout.write("Created port '%s' in DB:\n" % new_port)
        pprint.pprint_port(new_port, stdout=self.stdout)
        pprint.pprint_port_ips(new_port, stdout=self.stdout)
        self.stdout.write("\n")
        if vm is not None:
            common.wait_server_task(new_port.machine, wait, stdout=self.stdout)
