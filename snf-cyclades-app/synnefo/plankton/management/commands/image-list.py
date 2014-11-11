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

from snf_django.management.commands import SynnefoCommand
from snf_django.management.utils import pprint_table
from synnefo.plankton.backend import PlanktonBackend


class Command(SynnefoCommand):
    help = "List images."
    option_list = SynnefoCommand.option_list + (
        make_option(
            '--user',
            dest='userid',
            default=None,
            help="List only images that are available to this user."),
        make_option(
            '--public',
            dest='public',
            action="store_true",
            default=False,
            help="List only public images."),
    )

    def handle(self, **options):
        user = options['userid']
        check_perm = user is not None

        with PlanktonBackend(user) as backend:
            images = backend.list_images(user, check_permissions=check_perm)
            if options["public"]:
                images = filter(lambda x: x['is_public'], images)
            images.sort(key=lambda x: x['created_at'], reverse=True)

        headers = ("id", "name", "user.uuid", "public", "snapshot")
        table = []
        for img in images:
            fields = (img["id"], img["name"], img["owner"],
                      str(img["is_public"]), str(img["is_snapshot"]))
            table.append(fields)
        pprint_table(self.stdout, table, headers)
