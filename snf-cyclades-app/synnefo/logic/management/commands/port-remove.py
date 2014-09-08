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

from optparse import make_option
from django.core.management.base import CommandError
from synnefo.logic import servers
from synnefo.management import common
from snf_django.management.utils import parse_bool
from snf_django.management.commands import RemoveCommand


class Command(RemoveCommand):
    can_import_settings = True
    args = "<port_id> [<port_id> ...]"
    help = "Remove a port from the Database and from the VMs attached to"
    command_option_list = RemoveCommand.command_option_list + (
        make_option(
            "--wait",
            dest="wait",
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Wait for Ganeti jobs to complete. [Default: True]"),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if not args:
            raise CommandError("Please provide a port ID")

        force = options['force']
        message = "ports" if len(args) > 1 else "port"
        self.confirm_deletion(force, message, args)

        for port_id in args:
            self.stdout.write("\n")
            try:
                port = common.get_resource("port", port_id, for_update=True)

                servers.delete_port(port)

                wait = parse_bool(options["wait"])
                if port.machine is not None:
                    common.wait_server_task(port.machine, wait,
                                            stdout=self.stdout)
                else:
                    self.stdout.write("Successfully removed port %s\n" % port)
            except CommandError as e:
                self.stdout.write("Error -- %s\n" % e.message)
