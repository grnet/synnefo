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

from synnefo.db import transaction
from django.core.management.base import CommandError

from synnefo.management.common import (get_resource, convert_api_faults,
                                       wait_server_task)
from snf_django.management.commands import SynnefoCommand
from snf_django.management.utils import parse_bool
from synnefo.logic import servers


ACTIONS = ["start", "stop", "reboot_hard", "reboot_soft"]


class Command(SynnefoCommand):
    args = "<server_id>"
    help = "Modify a server."

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--name',
            dest='name',
            metavar='NAME',
            help="Rename server."),
        make_option(
            '--user',
            dest='user',
            metavar='USER_UUID',
            help="Change ownership of server. Value must be a user UUID"),
        make_option(
            "--suspended",
            dest="suspended",
            default=None,
            choices=["True", "False"],
            metavar="True|False",
            help="Mark a server as suspended/non-suspended."),
        make_option(
            "--flavor",
            dest="flavor",
            metavar="FLAVOR_ID",
            help="Resize a server by modifying its flavor. The new flavor"
                 " must have the same disk size and disk template."),
        make_option(
            "--action",
            dest="action",
            choices=ACTIONS,
            metavar="|".join(ACTIONS),
            help="Perform one of the allowed actions."),
        make_option(
            "--wait",
            dest="wait",
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Wait for Ganeti jobs to complete. [Default: True]"),
    )

    @transaction.commit_on_success
    @convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a server ID")

        server = get_resource("server", args[0], for_update=True)

        new_name = options.get("name", None)
        if new_name is not None:
            old_name = server.name
            server = servers.rename(server, new_name)
            self.stdout.write("Renamed server '%s' from '%s' to '%s'\n" %
                              (server, old_name, new_name))

        suspended = options.get("suspended", None)
        if suspended is not None:
            suspended = parse_bool(suspended)
            server.suspended = suspended
            server.save()
            self.stdout.write("Set server '%s' as suspended=%s\n" %
                              (server, suspended))

        new_owner = options.get('user')
        if new_owner is not None:
            if "@" in new_owner:
                raise CommandError("Invalid user UUID.")
            old_owner = server.userid
            server.userid = new_owner
            server.save()
            msg = "Changed the owner of server '%s' from '%s' to '%s'.\n"
            self.stdout.write(msg % (server, old_owner, new_owner))

        wait = parse_bool(options["wait"])
        new_flavor_id = options.get("flavor")
        if new_flavor_id is not None:
            new_flavor = get_resource("flavor", new_flavor_id)
            old_flavor = server.flavor
            msg = "Resizing server '%s' from flavor '%s' to '%s'.\n"
            self.stdout.write(msg % (server, old_flavor, new_flavor))
            server = servers.resize(server, new_flavor)
            wait_server_task(server, wait, stdout=self.stdout)

        action = options.get("action")
        if action is not None:
            if action == "start":
                server = servers.start(server)
            elif action == "stop":
                server = servers.stop(server)
            elif action == "reboot_hard":
                server = servers.reboot(server, reboot_type="HARD")
            elif action == "reboot_stof":
                server = servers.reboot(server, reboot_type="SOFT")
            else:
                raise CommandError("Unknown action.")
            wait_server_task(server, wait, stdout=self.stdout)
