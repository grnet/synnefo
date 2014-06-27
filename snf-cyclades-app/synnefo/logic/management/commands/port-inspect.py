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
from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from synnefo.management.common import convert_api_faults
from synnefo.management import pprint, common


class Command(SynnefoCommand):
    help = "Inspect a port on DB and Ganeti"
    args = "<port_id>"

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--jobs',
            action='store_true',
            dest='jobs',
            default=False,
            help="Show non-archived jobs concerning port."),
        make_option(
            '--display-mails',
            action='store_true',
            dest='displaymails',
            default=False,
            help="Display both uuid and email"),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a port ID")

        port = common.get_resource("port", args[0])
        display_mails = options['displaymails']

        pprint.pprint_port(port, display_mails=display_mails,
                           stdout=self.stdout)
        self.stdout.write('\n\n')

        pprint.pprint_port_ips(port, stdout=self.stdout)
        self.stdout.write('\n\n')

        pprint.pprint_port_in_ganeti(port, stdout=self.stdout)
