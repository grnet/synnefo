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

from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from synnefo.plankton.backend import PlanktonBackend
from synnefo.management import common
from snf_django.management import utils


class Command(SynnefoCommand):
    args = "<image_id>"
    help = "Display available information about an image"

    @common.convert_api_faults
    def handle(self, *args, **options):

        if len(args) != 1:
            raise CommandError("Please provide an image ID")
        image_id = args[0]

        try:
            with PlanktonBackend(None) as backend:
                image = backend.get_image(image_id, check_permissions=False)
        except:
            raise CommandError("An error occurred, verify that image or "
                               "user ID are valid")

        utils.pprint_table(out=self.stdout, table=[image.values()],
                           headers=image.keys(), vertical=True)
