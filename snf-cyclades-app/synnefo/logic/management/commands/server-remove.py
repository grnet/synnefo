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
from synnefo.management.common import (get_resource, convert_api_faults,
                                       wait_server_task)
from synnefo.logic import servers
from snf_django.management.commands import RemoveCommand
from snf_django.management.utils import parse_bool
from snf_django.lib.api import faults


class Command(RemoveCommand):
    args = "<server_id> [<server_id> ...]"
    help = "Remove a server by deleting the instance from the Ganeti backend."

    command_option_list = RemoveCommand.command_option_list + (
        make_option(
            '--wait',
            dest='wait',
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Wait for Ganeti job to complete. [Default: True]"),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if not args:
            raise CommandError("Please provide a server ID")

        force = options['force']
        message = "servers" if len(args) > 1 else "server"
        self.confirm_deletion(force, message, args)

        for server_id in args:
            self.stdout.write("\n")
            try:
                server = get_resource("server", server_id, for_update=True)

                self.stdout.write("Trying to remove server '%s' from backend "
                                  "'%s' \n" % (server.backend_vm_id,
                                               server.backend))

                server = servers.destroy(server)
                jobID = server.task_job_id

                self.stdout.write("Issued OP_INSTANCE_REMOVE with id: %s\n" %
                                  jobID)

                wait = parse_bool(options["wait"])
                wait_server_task(server, wait, self.stdout)
            except (CommandError, faults.BadRequest) as e:
                self.stdout.write("Error -- %s\n" % e.message)
