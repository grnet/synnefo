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
from synnefo.db.models import Network
from synnefo.api.networks import delete_network as api_delete_network
from synnefo.logic.backend import delete_network as backend_delete_network


class Command(BaseCommand):
    can_import_settings = True

    help = "Remove a network from the Database, and Ganeti"

    output_transaction = True  # The management command runs inside
                               # an SQL transaction

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("Please provide a network ID")

        try:
            network_id = int(args[0])
            network = Network.objects.get(id=network_id)
        except ValueError:
            raise CommandError("Invalid network ID")
        except network.DoesNotExist:
            raise CommandError("Network not found in DB")

        self.stdout.write('Trying to remove network: %s\n' % str(network))

        if network.machines.exists():
            raise CommandError('Network is not empty. Can not delete')

        if network.public:
            network.action = 'DESTROY'
            backend_delete_network(network)
        else:
            api_delete_network(network)

        self.stdout.write('Successfully removed network.\n')
