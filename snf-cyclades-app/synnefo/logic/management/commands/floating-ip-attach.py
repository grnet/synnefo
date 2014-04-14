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
from synnefo.logic import servers


class Command(SynnefoCommand):
    args = "<floating_ip_id>"
    help = "Attach a floating IP to a VM or router"

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--machine',
            dest='machine',
            default=None,
            help='The server id the floating-ip will be attached to'),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if not args or len(args) > 1:
            raise CommandError("Command accepts exactly one argument")

        floating_ip_id = args[0]  # this is the floating-ip address
        device = options['machine']

        if not device:
            raise CommandError('Please give either a server or a router id')

        #get the vm
        vm = common.get_resource("server", device, for_update=True)
        floating_ip = common.get_resource("floating-ip", floating_ip_id,
                                          for_update=True)
        servers.create_port(vm.userid, floating_ip.network,
                            use_ipaddress=floating_ip, machine=vm)

        self.stdout.write("Attached %s to %s.\n" % (floating_ip, vm))
