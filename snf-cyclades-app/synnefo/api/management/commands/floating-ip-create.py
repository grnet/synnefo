# Copyright 2012 GRNET S.A. All rights reserved.
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

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from synnefo.management.common import convert_api_faults

from synnefo.api import util
from synnefo.db import pools
from synnefo import quotas


class Command(BaseCommand):
    can_import_settings = True
    output_transaction = True

    help = "Allocate a new floating IP"

    option_list = BaseCommand.option_list + (
        make_option(
            '--pool',
            dest='pool',
            help="The IP pool to allocate the address from"),
        make_option(
            '--address',
            dest='address',
            help="The address to be allocated"),
        make_option(
            '--owner',
            dest='owner',
            default=None,
            # required=True,
            help='The owner of the floating IP'),
    )

    @transaction.commit_on_success
    @convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        pool = options['pool']
        address = options['address']
        owner = options['owner']

        if not owner:
            raise CommandError("'owner' is required for floating IP creation")

        if pool is None:
            if address:
                raise CommandError('Please specify a pool as well')

            # User did not specified a pool. Choose a random public IP
            try:
                floating_ip = util.allocate_public_ip(userid=owner,
                                                      floating_ip=True)
            except pools.EmptyPool:
                raise faults.Conflict("No more IP addresses available.")
        else:
            try:
                network_id = int(pool)
            except ValueError:
                raise CommandError("Invalid pool ID.")
            network = util.get_network(network_id, owner, for_update=True,
                                       non_deleted=True)
            if not network.floating_ip_pool:
                # Check that it is a floating IP pool
                raise CommandError("Floating IP pool %s does not exist." %
                                           network_id)
            floating_ip = util.allocate_ip(network, owner, address=address,
                                           floating_ip=True)

        quotas.issue_and_accept_commission(floating_ip)
        transaction.commit()

        self.stdout.write("Created floating IP '%s'.\n" % floating_ip)
