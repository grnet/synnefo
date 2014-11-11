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
    args = "<component ID or name>"
    help = "Modify component attributes"

    option_list = SynnefoCommand.option_list + (
        make_option('--ui-url',
                    dest='ui_url',
                    default=None,
                    help="Set UI URL"),
        make_option('--base-url',
                    dest='base_url',
                    help="Set base URL"),
        make_option('--auth-token',
                    dest='auth_token',
                    default=None,
                    help="Set a custom component auth token"),
        make_option('--renew-token',
                    action='store_true',
                    dest='renew_token',
                    default=False,
                    help="Renew component auth token"),
        make_option('--purge-services',
                    action='store_true',
                    dest='purge_services',
                    default=False,
                    help="Purge all services registered for this component"),
    )

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

        ui_url = options.get('ui_url')
        base_url = options.get('base_url')
        auth_token = options.get('auth_token')
        renew_token = options.get('renew_token')
        purge_services = options.get('purge_services')

        if not any([ui_url, base_url, auth_token, renew_token,
                    purge_services]):
            raise CommandError("No option specified.")

        if ui_url:
            component.url = ui_url

        if base_url:
            component.base_url = base_url

        if auth_token:
            component.auth_token = auth_token

        if renew_token and not auth_token:
            component.renew_token()

        component.save()

        if purge_services:
            component.service_set.all().delete()

        if renew_token:
            self.stdout.write(
                'Component\'s new token: %s\n' % component.auth_token
            )
