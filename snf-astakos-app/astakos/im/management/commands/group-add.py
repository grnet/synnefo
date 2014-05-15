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

from snf_django.management.commands import SynnefoCommand, CommandError
from astakos.im.models import Group


class Command(SynnefoCommand):
    args = "<group name>"
    help = "Create a group with the given name"

    option_list = SynnefoCommand.option_list + ()

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Invalid number of arguments")

        Group.objects.get_or_create(name=args[0].strip())
        self.stderr.write("Group created\n")
