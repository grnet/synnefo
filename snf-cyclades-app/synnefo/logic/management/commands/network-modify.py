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

from synnefo.db.models import Backend
from synnefo.management.common import get_resource
from snf_django.management.commands import SynnefoCommand
from snf_django.management.utils import parse_bool
from synnefo.logic import networks, backend as backend_mod
from django.db import transaction


class Command(SynnefoCommand):
    args = "<network_id>"
    help = "Modify a network."

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--name',
            dest='name',
            metavar='NAME',
            help="Rename a network"),
        make_option(
            '--user',
            dest='userid',
            help="Change the owner of the network."),
        make_option(
            "--drained",
            dest="drained",
            metavar="True|False",
            choices=["True", "False"],
            help="Set network as drained to prevent creation of new ports."),
        make_option(
            "--floating-ip-pool",
            dest="floating_ip_pool",
            metavar="True|False",
            choices=["True", "False"],
            help="Convert network to a floating IP pool. During this"
                 " conversion the network will be created to all"
                 " available Ganeti backends."),
        make_option(
            '--add-reserved-ips',
            dest="add_reserved_ips",
            help="Comma seperated list of IPs to externally reserve."),
        make_option(
            '--remove-reserved-ips',
            dest="remove_reserved_ips",
            help="Comma seperated list of IPs to externally release."),
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

        network = get_resource("network", args[0])

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
                if network.ips.filter(deleted=False, floating_ip=True)\
                              .exists():
                    msg = ("Cannot make network a non floating IP pool."
                           " There are still reserved floating IPs.")
                    raise CommandError(msg)
            network.floating_ip_pool = floating_ip_pool
            network.save()
            self.stdout.write("Set network '%s' as floating-ip-pool=%s.\n" %
                              (network, floating_ip_pool))
            if floating_ip_pool is True:
                for backend in Backend.objects.filter(offline=False):
                    bnet, jobs =\
                        backend_mod.ensure_network_is_active(backend,
                                                             network.id)
                    if jobs:
                        msg = ("Sent job to create network '%s' in backend"
                               " '%s'\n" % (network, backend))
                        self.stdout.write(msg)

        add_reserved_ips = options.get('add_reserved_ips')
        remove_reserved_ips = options.get('remove_reserved_ips')
        if add_reserved_ips or remove_reserved_ips:
            if add_reserved_ips:
                add_reserved_ips = add_reserved_ips.split(",")
                for ip in add_reserved_ips:
                    network.reserve_address(ip, external=True)
            if remove_reserved_ips:
                remove_reserved_ips = remove_reserved_ips.split(",")
                for ip in remove_reserved_ips:
                    network.release_address(ip, external=True)

        add_to_backend = options["add_to_backend"]
        if add_to_backend is not None:
            backend = get_resource("backend", add_to_backend)
            bnet, jobs = backend_mod.ensure_network_is_active(backend,
                                                              network.id)
            if jobs:
                msg = "Sent job to create network '%s' in backend '%s'\n"
                self.stdout.write(msg % (network, backend))

        remove_from_backend = options["remove_from_backend"]
        if remove_from_backend is not None:
            backend = get_resource("backend", remove_from_backend)
            if network.nics.filter(machine__backend=backend,
                                   machine__deleted=False).exists():
                msg = "Cannot remove. There are still connected VMs to this"\
                      " network"
                raise CommandError(msg)
            backend_mod.delete_network(network, backend, disconnect=True)
            msg = "Sent job to delete network '%s' from backend '%s'\n"
            self.stdout.write(msg % (network, backend))
