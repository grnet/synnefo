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
from synnefo.management.common import convert_api_faults
from synnefo.management import pprint, common
from synnefo.volume import volumes


class Command(SynnefoCommand):
    help = "Modify a volume"
    args = "<volume ID>"

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--name',
            dest='name',
            help="Modify a volume's display name"),
        make_option(
            '--description',
            dest='description',
            help="Modify a volume's display description"),
        make_option(
            '--delete-on-termination',
            dest='delete_on_termination',
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Set whether volume will be preserved when the server"
                 " the volume is attached will be deleted"),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a volume ID")

        volume = common.get_resource("volume", args[0], for_update=True)

        name = options.get("name")
        description = options.get("description")
        delete_on_termination = options.get("delete_on_termination")
        if delete_on_termination is not None:
            delete_on_termination = parse_bool(delete_on_termination)

        volume = volumes.update(volume, name, description,
                                delete_on_termination)

        pprint.pprint_volume(volume, stdout=self.stdout)
        self.stdout.write('\n\n')
