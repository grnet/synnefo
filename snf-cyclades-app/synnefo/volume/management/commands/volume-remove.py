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
from synnefo.volume import volumes
from synnefo.management import common
from snf_django.management.utils import parse_bool
from snf_django.management.commands import RemoveCommand


class Command(RemoveCommand):
    can_import_settings = True
    args = "<Volume ID> [<Volume ID> ...]"
    help = "Remove a volume from the Database and from the VM attached to"
    option_list = RemoveCommand.option_list + (
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

        force = options['force']
        message = "volumes" if len(args) > 1 else "volume"
        self.confirm_deletion(force, message, args)

        for volume_id in args:
            self.stdout.write("\n")
            try:
                volume = common.get_resource("volume", volume_id,
                                             for_update=True)
                volumes.delete(volume)

                wait = parse_bool(options["wait"])
                if volume.machine is not None:
                    volume.machine.task_job_id = volume.backendjobid
                    common.wait_server_task(volume.machine, wait,
                                            stdout=self.stdout)
                else:
                    self.stdout.write("Successfully removed volume %s\n"
                                      % volume)
            except CommandError as e:
                self.stdout.write("Error -- %s\n" % e.message)
