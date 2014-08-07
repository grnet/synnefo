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

from snf_django.management.commands import SynnefoCommand, CommandError
from optparse import make_option

from synnefo.management import common
from synnefo.plankton.backend import PlanktonBackend
from snf_django.management import utils


class Command(SynnefoCommand):
    args = "<snapshot_id>"
    help = "Display available information about a snapshot"
    option_list = SynnefoCommand.option_list + (
        make_option(
            '--user',
            dest='userid',
            default=None,
            help="The UUID of the owner of the snapshot. Required"
                 "if snapshot is not public"),
        make_option(
            '--public',
            dest='public',
            default=False,
            action="store_true",
            help="Use this option if the snapshot is public"),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):

        if len(args) != 1:
            raise CommandError("Please provide a snapshot ID")

        snapshot_id = args[0]
        userid = options["userid"]
        public = options["public"]

        if (userid is None) and (public is False):
            raise CommandError("'user' option or 'public' option is required")

        try:
            with PlanktonBackend(userid) as backend:
                snapshot = backend.get_snapshot(snapshot_id)
        except:
            raise CommandError("An error occurred, verify that snapshot and "
                               "user ID are valid")

        utils.pprint_table(out=self.stdout, table=[snapshot.values()],
                           headers=snapshot.keys(), vertical=True)
