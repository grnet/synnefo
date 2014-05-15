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

#from optparse import make_option

from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from synnefo.management import common
from synnefo.logic import servers


class Command(SynnefoCommand):
    args = "<floating_ip_id>"
    help = "Detach a floating IP from a VM or router"

    @common.convert_api_faults
    def handle(self, *args, **options):
        if not args or len(args) > 1:
            raise CommandError("Command accepts exactly one argument")

        floating_ip_id = args[0]

        #get the floating-ip
        floating_ip = common.get_resource("floating-ip", floating_ip_id,
                                          for_update=True)

        if not floating_ip.nic:
            raise CommandError('This floating IP is not attached to a device')

        nic = floating_ip.nic
        vm = nic.machine
        servers.delete_port(nic)
        self.stdout.write("Detached floating IP %s from  %s.\n"
                          % (floating_ip_id, vm))
