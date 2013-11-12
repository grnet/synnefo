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

from synnefo.api import util
from synnefo.management import common, pprint
from snf_django.management.utils import parse_bool
from synnefo.logic import servers

HELP_MSG = """Create a new port.

Connect a server/router to a network by creating a new port. If 'floating_ip'
option is used, the specified floating IP will be assigned to the new port.
Otherwise, the port will get an IP address for each Subnet that is associated
with the network."""


class Command(BaseCommand):
    help = HELP_MSG

    option_list = BaseCommand.option_list + (
        make_option(
            "--name",
            dest="name",
            default=None,
            help="Name of the port."),
        make_option(
            "--owner",
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
            help="Wait for Ganeti jobs to complete."),
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

        if user_id is None:
            raise CommandError("Please specify the owner of the port")

        vm = None
        owner = None
        if server_id:
            owner = "vm"
            vm = common.get_vm(server_id)
            #if vm.router:
            #    raise CommandError("Server '%s' does not exist." % server_id)
        elif router_id:
            owner = "router"
            vm = common.get_vm(router_id)
            if not vm.router:
                raise CommandError("Router '%s' does not exist." % router_id)

        # get the network
        network = common.get_network(network_id)

        # Get either floating IP or fixed ip address
        ipaddress = None
        floating_ip_id = options["floating_ip_id"]
        ipv4_address = options["ipv4_address"]
        if ipv4_address is not None and floating_ip_id is not None:
            raise CommandError("Please use either --floating-ip-id or"
                               " --ipv4-address option")
        elif floating_ip_id:
            ipaddress = common.get_floating_ip_by_id(floating_ip_id,
                                                     for_update=True)

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
