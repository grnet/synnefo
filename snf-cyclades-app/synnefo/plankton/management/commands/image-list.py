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
    help = "List public images or images available to a user."
    option_list = SynnefoCommand.option_list + (
        make_option(
            '--user',
            dest='userid',
            default=None,
            help="List all images available to that user."
                 " If no user is specified, only public images"
                 " are displayed."),
    )

    def handle(self, **options):
        user = options['userid']

        with PlanktonBackend(user) as backend:
            images = backend._list_images(user)
            images.sort(key=lambda x: x['created_at'], reverse=True)

        headers = ("id", "name", "user.uuid", "public", "snapshot")
        table = []
        for img in images:
            fields = (img["id"], img["name"], img["owner"],
                      str(img["is_public"]), str(img["is_snapshot"]))
            table.append(fields)
        pprint_table(self.stdout, table, headers)
