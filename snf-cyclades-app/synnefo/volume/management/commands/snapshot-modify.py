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
from synnefo.volume import snapshots, util
from synnefo.management import common
from snf_django.management.commands import SynnefoCommand


class Command(SynnefoCommand):
    args = "<Snapshot ID>"
    help = "Modify a snapshot"
    option_list = SynnefoCommand.option_list + (
        make_option(
            "--user",
            dest="user",
            default=None,
            help="UUID of the owner of the snapshot"),
        make_option(
            "--name",
            dest="name",
            default=None,
            help="Update snapshot's name"),
        make_option(
            "--description",
            dest="description",
            default=None,
            help="Update snapshot's description"),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if not args:
            raise CommandError("Please provide a snapshot ID")

        snapshot_id = args[0]
        userid = options["user"]
        name = options["name"]
        description = options["description"]

        snapshot = util.get_snapshot(userid, snapshot_id)

        snapshots.update(snapshot, name=name, description=description)
        self.stdout.write("Successfully updated snapshot %s\n"
                          % snapshot_id)
