# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.
#

from django.core.management.base import BaseCommand, CommandError
from synnefo.management.common import get_backend
from synnefo.logic import backend as backend_mod
from synnefo.db.models import Backend
from django.db import transaction, models


HELP_MSG = """\
Remove a backend from the Database. Backend should be set to drained before
trying to remove it, in order to avoid the allocation of a new instances in
this Backend.  Removal of a backend will fail if the backend hosts any
non-deleted instances."""


class Command(BaseCommand):
    help = HELP_MSG

    def handle(self, *args, **options):
        write = self.stdout.write
        if len(args) < 1:
            raise CommandError("Please provide a backend ID")

        backend = get_backend(args[0])

        write("Trying to remove backend: %s\n" % backend.clustername)

        if backend.virtual_machines.filter(deleted=False).exists():
            raise CommandError('Backend hosts non-deleted vms. Can not delete')

        # Get networks before deleting backend, because after deleting the
        # backend, all BackendNetwork objects are deleted!
        networks = [bn.network for bn in backend.networks.all()]

        try:
            delete_backend(backend)
        except models.ProtectedError as e:
            msg = ("Can not delete backend because it contains"
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
