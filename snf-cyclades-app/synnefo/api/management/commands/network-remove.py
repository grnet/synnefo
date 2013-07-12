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
from synnefo.logic.backend import delete_network
from synnefo.management.common import get_network
from synnefo import quotas


class Command(BaseCommand):
    can_import_settings = True

    help = "Remove a network from the Database, and Ganeti"

    output_transaction = True  # The management command runs inside
                               # an SQL transaction

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("Please provide a network ID")

        network = get_network(args[0])

        self.stdout.write('Trying to remove network: %s\n' % str(network))

        if network.machines.exists():
            raise CommandError('Network is not empty. Can not delete')

        network.action = 'DESTROY'
        network.save()

        if network.userid:
            quotas.issue_and_accept_commission(network, delete=True)

        for bnet in network.backend_networks.exclude(operstate="DELETED"):
            delete_network(network, bnet.backend)

        self.stdout.write("Successfully submitted Ganeti jobs to"
                          " remove network %s" % network.backend_id)
