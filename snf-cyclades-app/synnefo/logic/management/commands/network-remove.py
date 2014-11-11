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
from snf_django.management.commands import RemoveCommand
from snf_django.lib.api import faults
from synnefo.logic import networks
from synnefo.management import common


class Command(RemoveCommand):
    can_import_settings = True
    args = "<network_id> [<network_id> ...]"
    help = "Remove a network from the Database, and Ganeti"

    @common.convert_api_faults
    def handle(self, *args, **options):
        if not args:
            raise CommandError("Please provide a network ID")

        force = options['force']
        message = "networks" if len(args) > 1 else "network"
        self.confirm_deletion(force, message, args)

        for network_id in args:
            self.stdout.write("\n")
            try:
                network = common.get_resource("network", network_id,
                                              for_update=True)
                self.stdout.write('Removing network: %s\n' %
                                  network.backend_id)

                networks.delete(network)

                self.stdout.write("Successfully submitted Ganeti jobs to"
                                  " remove network %s\n" % network.backend_id)
            except (CommandError, faults.BadRequest) as e:
                self.stdout.write("Error -- %s\n" % e.message)
