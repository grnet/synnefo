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

from synnefo.db.models import (Backend, BackendNetwork, pooled_rapi_client)
from synnefo.management.common import (get_network, get_backend)
from snf_django.management.utils import parse_bool
from synnefo.logic import networks, backend as backend_mod
from django.db import transaction


class Command(BaseCommand):
    args = "<network id>"
    help = "Modify a network."

    option_list = BaseCommand.option_list + (
        make_option(
            '--name',
            dest='name',
            metavar='NAME',
            help="Rename a network"),
        make_option(
            '--userid',
            dest='userid',
            help="Change the owner of the network."),
        make_option(
            "--drained",
            dest="drained",
            metavar="True|False",
            choices=["True", "False"],
            help="Set as drained to exclude for IP allocation."
                 " Only used for public networks."),
        make_option(
            "--floating-ip-pool",
            dest="floating_ip_pool",
            metavar="True|False",
            choices=["True", "False"],
            help="Convert network to a floating IP pool. During this"
                 " conversation the network will be created to all"
                 " available Ganeti backends."),
        make_option(
            "--add-to-backend",
            dest="add_to_backend",
            metavar="BACKEND_ID",
            help="Create a network to a Ganeti backend."),
        make_option(
            "--remove-from-backend",
            dest="remove_from_backend",
            metavar="BACKEND_ID",
            help="Remove a network from a Ganeti backend."),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a network ID")

        network = get_network(args[0])

        new_name = options.get("name")
        if new_name is not None:
            old_name = network.name
            network = networks.rename(network, new_name)
            self.stdout.write("Renamed network '%s' from '%s' to '%s'.\n" %
                              (network, old_name, new_name))

        drained = options.get("drained")
        if drained is not None:
            drained = parse_bool(drained)
            network.drained = drained
            network.save()
            self.stdout.write("Set network '%s' as drained=%s.\n" %
                              (network, drained))

        new_owner = options.get("userid")
        if new_owner is not None:
            if "@" in new_owner:
                raise CommandError("Invalid owner UUID.")
            old_owner = network.userid
            network.userid = new_owner
            network.save()
            msg = "Changed the owner of network '%s' from '%s' to '%s'.\n"
            self.stdout.write(msg % (network, old_owner, new_owner))

        floating_ip_pool = options["floating_ip_pool"]
        if floating_ip_pool is not None:
            floating_ip_pool = parse_bool(floating_ip_pool)
            if floating_ip_pool is False and network.floating_ip_pool is True:
                if network.floating_ips.filter(deleted=False).exists():
                    msg = ("Can not make network a non floating IP pool."
                           " There are still reserved floating IPs.")
                    raise CommandError(msg)
            network.floating_ip_pool = floating_ip_pool
            network.save()
            self.stdout.write("Set network '%s' as floating-ip-pool=%s.\n" %
                              (network, floating_ip_pool))
            if floating_ip_pool is True:
                for backend in Backend.objects.filter(offline=False):
                    try:
                        bnet = network.backend_networks.get(backend=backend)
                    except BackendNetwork.DoesNotExist:
                        bnet = network.create_backend_network(backend=backend)
                    if bnet.operstate != "ACTIVE":
                        backend_mod.create_network(network, backend,
                                                   connect=True)
                        msg = ("Sent job to create network '%s' in backend"
                               " '%s'\n" % (network, backend))
                        self.stdout.write(msg)

        add_to_backend = options["add_to_backend"]
        if add_to_backend is not None:
            backend = get_backend(add_to_backend)
            network.create_backend_network(backend=backend)
            backend_mod.create_network(network, backend, connect=True)
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
            backend_mod.delete_network(network, backend, disconnect=True)
            msg = "Sent job to delete network '%s' from backend '%s'\n"
            self.stdout.write(msg % (network, backend))
