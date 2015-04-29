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

import distutils
from optparse import make_option
from django.core.management.base import CommandError
from synnefo.volume import volumes
from synnefo.management import common
from snf_django.management.utils import parse_bool
from snf_django.management.commands import SynnefoCommand


HELP_MSG = "Detach a volume from a server"


class Command(SynnefoCommand):
    #umask = 0o007
    can_import_settings = True
    args = "<Volume ID> [<Volume ID> ...]"
    option_list = SynnefoCommand.option_list + (
        make_option(
            "--wait",
            dest="wait",
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Wait for Ganeti jobs to complete."),
        make_option(
            "-f", "--force",
            dest="force",
            action="store_true",
            default=False,
            help="Do not prompt for confirmation"),
    )

    def confirm_detachment(self, force, resource='', args=''):
        if force is True:
            return True

        ids = ', '.join(args)
        self.stdout.write("Are you sure you want to detach %s %s?"
                          " [Y/N] " % (resource, ids))
        try:
            answer = distutils.util.strtobool(raw_input())
            if answer != 1:
                raise CommandError("Aborting detachment")
        except ValueError:
            raise CommandError("Unaccepted input value. Please choose yes/no"
                               " (y/n).")

    @common.convert_api_faults
    def handle(self, *args, **options):
        if not args:
            raise CommandError("Please provide a volume ID")

        force = options['force']
        message = "volumes" if len(args) > 1 else "volume"
        self.confirm_detachment(force, message, args)

        for volume_id in args:
            self.stdout.write("\n")
            try:
                volume = volumes.detach(volume_id)

                wait = parse_bool(options["wait"])
                if volume.machine is not None:
                    volume.machine.task_job_id = volume.backendjobid
                    common.wait_server_task(volume.machine, wait,
                                            stdout=self.stdout)
                else:
                    self.stdout.write("Successfully detached volume %s\n"
                                      % volume)
            except CommandError as e:
                self.stdout.write("Error -- %s\n" % e.message)
