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
from synnefo.management.common import convert_api_faults

from synnefo.api import util
from synnefo.management.common import get_network, get_vm
from synnefo.logic import ports

HELP_MSG = """Create a new port.

Connect a server/router to a network by creating a new port. The port will
get an IP address for each Subnet that is associated with the network."""


class Command(BaseCommand):
    help = HELP_MSG

    option_list = BaseCommand.option_list + (
        make_option(
            "--name",
            dest="name",
            default=None,
            help="Name of the port."),
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
        make_option(
            "--router",
            dest="router_id",
            default=None,
            help="The ID of the router that the port will be connected to."),
        make_option(
            "--security-groups",
            dest="security-groups",
            default=None,
            help="Comma separated list of Security Group IDs to associate"
                 " with the port."),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        name = options["name"]
        network_id = options["network_id"]
        server_id = options["server_id"]
        router_id = options["router_id"]
        # assume giving security groups comma separated
        security_group_ids = options["security-groups"]

        if not name:
            name = ""

        if (server_id and router_id) or not (server_id or router_id):
            raise CommandError("Please give either a server or a router id")

        if not network_id:
            raise CommandError("Please specify a 'network'")

        if server_id:
            owner = "vm"
            vm = get_vm(server_id)
            if vm.router:
                raise CommandError("Server '%s' does not exist." % server_id)
        elif router_id:
            owner = "router"
            vm = get_vm(router_id)
            if not vm.router:
                raise CommandError("Router '%s' does not exist." % router_id)
        else:
            raise CommandError("Neither server or router is specified")

        # get the network
        network = get_network(network_id)

        # validate security groups
        sg_list = []
        if security_group_ids:
            security_group_ids = security_group_ids.split(",")
            for gid in security_group_ids:
                sg = util.get_security_group(int(gid))
                sg_list.append(sg)

        new_port = ports.create(network, vm, name, security_groups=sg_list,
                                device_owner=owner)
        self.stdout.write("Created port '%s' in DB.\n" % new_port)
        # TODO: Display port information, like ip address
        # TODO: Add --wait argument to report progress about the Ganeti job.
