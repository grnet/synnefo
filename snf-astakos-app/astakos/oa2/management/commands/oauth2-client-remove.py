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

from astakos.oa2.models import Client


class Command(SynnefoCommand):
    args = "<client ID or identifier>"
    help = "Remove an oauth2 client along with its registered redirect urls"

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a client ID or identifier")

        ident = args[0]
        try:
            try:
                ident = int(ident)
                client = Client.objects.get(id=ident)
            except ValueError:
                client = Client.objects.get(identifier=ident)
        except Client.DoesNotExist:
            raise CommandError(
                "Client does not exist. You may run snf-manage "
                "oa2-client-list for available client IDs.")

        client.redirecturl_set.all().delete()
        client.authorizationcode_set.all().delete()
        client.token_set.all().delete()
        client.delete()
