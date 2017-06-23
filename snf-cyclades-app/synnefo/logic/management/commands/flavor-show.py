# Copyright (C) 2010-2017 GRNET S.A.
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

from snf_django.management.commands import SynnefoCommand
from django.core.management.base import CommandError

from synnefo.management.common import convert_api_faults
from synnefo.management import pprint, common


class Command(SynnefoCommand):
    help = "Show Flavor information"
    args = "<Flavor ID>"

    @convert_api_faults
    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("Please provide a flavor ID")

        flavor = common.get_resource("flavor", args[0])

        pprint.pprint_flavor(flavor, stdout=self.stdout)
