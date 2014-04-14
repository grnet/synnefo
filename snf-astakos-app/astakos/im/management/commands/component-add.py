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
from astakos.im.models import Component


class Command(SynnefoCommand):
    args = "<name>"
    help = "Register a component"

    option_list = SynnefoCommand.option_list + (
        make_option('--ui-url',
                    dest='ui_url',
                    default=None,
                    help="Set UI URL"),
        make_option('--base-url',
                    dest='base_url',
                    default=None,
                    help="Set base URL"),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Invalid number of arguments")

        name = args[0]
        base_url = options['base_url']
        ui_url = options['ui_url']

        try:
            Component.objects.get(name=name)
            m = "There already exists a component named '%s'." % name
            raise CommandError(m)
        except Component.DoesNotExist:
            pass

        try:
            c = Component.objects.create(
                name=name, url=ui_url, base_url=base_url)
        except BaseException:
            raise CommandError("Failed to register component.")
        else:
            self.stdout.write('Token: %s\n' % c.auth_token)
