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
from synnefo.management import common
from synnefo.management import pprint


class Command(SynnefoCommand):
    help = "Inspect a server on DB and Ganeti"
    args = "<server_id>"

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--jobs',
            action='store_true',
            dest='jobs',
            default=False,
            help="Show non-archived jobs concerning server."),
        make_option(
            '--display-mails',
            action='store_true',
            dest='displaymails',
            default=False,
            help="Display both uuid and email"),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a server ID")

        vm = common.get_resource("server", args[0], for_update=True)

        display_mails = options['displaymails']

        pprint.pprint_server(vm, display_mails=display_mails, stdout=self.stdout)
        self.stdout.write("\n")
        pprint.pprint_server_nics(vm, stdout=self.stdout)
        self.stdout.write("\n")
        pprint.pprint_server_volumes(vm, stdout=self.stdout)
        self.stdout.write("\n")
        pprint.pprint_server_in_ganeti(vm, print_jobs=options["jobs"],
                                       stdout=self.stdout)
        self.stdout.write("\n")
