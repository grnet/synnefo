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
from astakos.im import transaction
from astakos.im.models import Component


class Command(SynnefoCommand):
    args = "<component ID or name>"
    help = "Remove a component along with its registered services"

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a component ID or name")

        ident = args[0]
        try:
            try:
                ident = int(ident)
                component = Component.objects.get(id=ident)
            except ValueError:
                component = Component.objects.get(name=ident)
        except Component.DoesNotExist:
            raise CommandError(
                "Component does not exist. You may run snf-manage "
                "component-list for available component IDs.")

        component.delete()
