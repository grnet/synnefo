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
from synnefo.db.models import Backend, VirtualMachine, BackendNetwork


class Command(BaseCommand):
    can_import_settings = True

    help = "Remove a backend from the Database. Backend should be set\n" \
           "to drained before trying to remove it, in order to avoid the\n" \
           "allocation of a new instances in this Backend.\n\n" \
           "Removal of a backend will fail if the backend hosts any\n" \
           "non-deleted instances."

    output_transaction = True  # The management command runs inside
                               # an SQL transaction

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("Please provide a backend ID")

        try:
            backend_id = int(args[0])
            backend = Backend.objects.get(id=backend_id)
        except ValueError:
            raise CommandError("Invalid backend ID")
        except Backend.DoesNotExist:
            raise CommandError("Backend not found in DB")

        self.stdout.write('Trying to remove backend: %s\n' % backend.clustername)

        vms_in_backend = VirtualMachine.objects.filter(backend=backend,
                                                       deleted=False)

        if vms_in_backend:
            raise CommandError('Backend hosts non-deleted vms. Can not delete')

        networks = BackendNetwork.objects.filter(backend=backend, deleted=False)
        networks = [net.network.backend_id for net in networks]

        backend.delete()

        self.stdout.write('Successfully removed backend.\n')

        if networks:
            self.stdout.write('Left the following orphans networks in Ganeti:\n')
            self.stdout.write('  ' + '\n  * '.join(networks) + '\n')
            self.stdout.write('Manually remove them.\n')
