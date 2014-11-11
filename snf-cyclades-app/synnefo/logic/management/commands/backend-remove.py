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
#

from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from synnefo.management import common
from synnefo.logic import backend as backend_mod
from synnefo.db.models import Backend
from django.db import models
from synnefo.db import transaction


HELP_MSG = """\
Remove a backend from the Database. Backend should be set to drained before
trying to remove it, in order to avoid the allocation of a new instances in
this Backend.  Removal of a backend will fail if the backend hosts any
non-deleted instances."""


class Command(SynnefoCommand):
    args = "<backend_id>"
    help = HELP_MSG

    def handle(self, *args, **options):
        write = self.stdout.write
        if len(args) < 1:
            raise CommandError("Please provide a backend ID")

        backend = common.get_resource("backend", args[0], for_update=True)

        write("Trying to remove backend: %s\n" % backend.clustername)

        if backend.virtual_machines.filter(deleted=False).exists():
            raise CommandError('Backend hosts non-deleted vms. Cannot delete')

        # Get networks before deleting backend, because after deleting the
        # backend, all BackendNetwork objects are deleted!
        networks = [bn.network for bn in backend.networks.all()]

        try:
            delete_backend(backend)
        except models.ProtectedError as e:
            msg = ("Cannot delete backend because it contains"
                   "non-deleted VMs:\n%s" % e)
            raise CommandError(msg)

        write('Successfully removed backend from DB.\n')

        if networks:
            write("Clearing networks from %s..\n" % backend.clustername)
            for network in networks:
                backend_mod.delete_network(network=network, backend=backend)
            write("Successfully issued jobs to remove all networks.\n")


@transaction.commit_on_success
def delete_backend(backend):
    # Get X-Lock
    backend = Backend.objects.select_for_update().get(id=backend.id)
    # Clear 'backend' field of 'deleted' VirtualMachines
    backend.virtual_machines.filter(deleted=True).update(backend=None)
    # Delete all BackendNetwork objects of this backend
    backend.networks.all().delete()
    backend.delete()
