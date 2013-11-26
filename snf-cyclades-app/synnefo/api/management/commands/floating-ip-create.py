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

from django.core.management.base import BaseCommand, CommandError
from synnefo.management.common import convert_api_faults
from synnefo.logic import ips
from synnefo.api import util


class Command(BaseCommand):
    help = "Allocate a new floating IP"

    option_list = BaseCommand.option_list + (
        make_option(
            '--pool',
            dest='pool',
            help="The ID of the floating IP pool(network) to allocate the"
                 " address from"),
        make_option(
            '--address',
            dest='address',
            help="The address to be allocated"),
        make_option(
            '--owner',
            dest='owner',
            default=None,
            help='The owner of the floating IP'),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        network_id = options['pool']
        address = options['address']
        owner = options['owner']

        if not owner:
            raise CommandError("'owner' is required for floating IP creation")

        if network_id is not None:
            network = util.get_network(network_id, owner, for_update=True,
                                       non_deleted=True)
        else:
            network = None

        floating_ip = ips.create_floating_ip(userid=owner,
                                             network=network,
                                             address=address)

        self.stdout.write("Created floating IP '%s'.\n" % floating_ip)
