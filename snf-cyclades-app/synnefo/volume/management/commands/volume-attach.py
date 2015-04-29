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

from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.management.utils import parse_bool
from synnefo.volume import volumes
from synnefo.management import common

HELP_MSG = """Attach an existing volume to a server."""


class Command(SynnefoCommand):
    help = HELP_MSG
    umask = 0o007

    option_list = SynnefoCommand.option_list + (
        make_option(
            "--server",
            dest="server_id",
            default=None,
            help="The ID of the server that the volume will be connected to."),
        make_option(
            "--wait",
            dest="wait",
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Wait for Ganeti jobs to complete."),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if not args:
            raise CommandError("Please provide a volume ID")

        server_id = options.get("server_id")
        wait = parse_bool(options["wait"])

        if not server_id:
            raise CommandError("Please provide a server ID")

        for volume_id in args:
            try:
                volume = volumes.attach(server_id, volume_id)

                if volume.machine is None:
                    volume.machine.task_job_id = volume.backendjobid
                    common.wait_server_task(volume.machine, wait,
                                            stdout=self.stdout)
                else:
                    self.stdout.write("Successfully attached volume %s\n"
                                      % volume)
            except CommandError as e:
                self.stdout.write("Error -- %s\n" % e.message)
