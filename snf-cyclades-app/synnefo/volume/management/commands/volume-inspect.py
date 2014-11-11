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

from synnefo.management.common import convert_api_faults
from synnefo.management import pprint, common


class Command(SynnefoCommand):
    help = "Inspect a Volume on DB and Ganeti"
    args = "<volume ID>"

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--display-mails',
            action='store_true',
            dest='displaymail',
            default=False,
            help="Display both uuid and email"),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a volume ID")

        volume = common.get_resource("volume", args[0])

        pprint.pprint_volume(volume, stdout=self.stdout,
                             display_mails=options['displaymail'])
        self.stdout.write('\n\n')

        pprint.pprint_volume_in_ganeti(volume, stdout=self.stdout)
