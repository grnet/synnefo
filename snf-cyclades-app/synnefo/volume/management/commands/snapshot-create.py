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
from synnefo.management import common
#from snf_django.management.utils import parse_bool
from synnefo.volume import snapshots


class Command(SynnefoCommand):
    args = "<volume ID>"
    help = "Create a snapshot from the specified volume"

    option_list = SynnefoCommand.option_list + (
        make_option(
            "--name",
            dest="name",
            default=None,
            help="Display name of the snapshot"),
        make_option(
            "--description",
            dest="description",
            default=None,
            help="Display description of the snapshot"),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a volume ID")

        volume = common.get_resource("volume", args[0], for_update=True)

        name = options.get("name")
        if name is None:
            raise CommandError("'name' option is required")

        description = options.get("description")
        if description is None:
            description = "Snapshot of Volume '%s'" % volume.id

        snapshot = snapshots.create(volume.userid,
                                    volume,
                                    name=name,
                                    description=description,
                                    metadata={})

        msg = ("Created snapshot of volume '%s' with ID %s\n"
               % (volume.id, snapshot["id"]))
        self.stdout.write(msg)
