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

from snf_django.management.commands import SynnefoCommand
from optparse import make_option

from snf_django.management.utils import pprint_table
from synnefo.plankton.backend import PlanktonBackend


class Command(SynnefoCommand):
    help = "List snapshots."
    option_list = SynnefoCommand.option_list + (
        make_option(
            '--user',
            dest='userid',
            default=None,
            help="List only snapshots that are available to this user."),
        make_option(
            '--public',
            dest='public',
            action="store_true",
            default=False,
            help="List only public snapshots."),
    )

    def handle(self, **options):
        user = options['userid']
        check_perm = user is not None

        with PlanktonBackend(user) as backend:
            snapshots = backend.list_snapshots(user,
                                               check_permissions=check_perm)
            if options['public']:
                snapshots = filter(lambda x: x['is_public'], snapshots)

        headers = ("id", "name", "volume_id", "size", "mapfile", "status",
                   "owner", "is_public")
        table = []
        for snap in snapshots:
            fields = (snap["id"], snap["name"], snap["volume_id"],
                      snap["size"], snap["mapfile"], snap["status"],
                      snap["owner"], snap["is_public"])
            table.append(fields)
        pprint_table(self.stdout, table, headers)
