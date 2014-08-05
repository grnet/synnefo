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

from snf_django.management.commands import SynnefoCommand
from synnefo.management import common
from synnefo.logic import ips


class Command(SynnefoCommand):
    help = "Allocate a new floating IP"

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--network',
            dest='network_id',
            help="The ID of the network to allocate the address from"),
        make_option(
            '--address',
            dest='address',
            help="The address to be allocated"),
        make_option(
            '--user',
            dest='user',
            default=None,
            help='The owner of the floating IP'),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        network_id = options['network_id']
        address = options['address']
        user = options['user']

        if not user:
            raise CommandError("'user' is required for floating IP creation")

        if network_id is not None:
            network = common.get_resource("network", network_id,
                                          for_update=True)
            if network.deleted:
                raise CommandError("Network '%s' is deleted" % network.id)
            if not network.floating_ip_pool:
                raise CommandError("Network '%s' is not a floating IP pool."
                                   % network)
        else:
            network = None

        floating_ip = ips.create_floating_ip(userid=user,
                                             network=network,
                                             address=address)

        self.stdout.write("Created floating IP '%s'.\n" % floating_ip)
