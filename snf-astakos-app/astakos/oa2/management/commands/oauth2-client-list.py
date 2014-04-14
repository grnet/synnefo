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

from snf_django.management.commands import ListCommand

from astakos.oa2.models import Client


def get_redirect_urls(client):
    return ','.join(client.redirecturl_set.values_list('url', flat=True))


class Command(ListCommand):
    help = "List oauth2 clients"

    object_class = Client

    FIELDS = {
        'id': ('id', ('The id of the client')),
        'identifier': ('identifier', 'The unique client identifier'),
        'type': ('type', 'The client type'),
        'is_trusted': ('is_trusted', 'Whether the client is trusted or not'),
        'redirect_urls': (get_redirect_urls, 'The registered redirect URLs')
    }

    fields = ['id', 'identifier', 'type', 'is_trusted']

    option_list = ListCommand.option_list + (
        make_option('--confidential',
                    action='store_true',
                    dest='confidential',
                    default=False,
                    help="Display only confidential clients"),
        make_option('--public',
                    action='store_true',
                    dest='public',
                    default=False,
                    help="Display only public clients"),
        make_option('--trusted',
                    action='store_true',
                    dest='trusted',
                    default=False,
                    help="Display only trusted clients"),
    )

    def handle_args(self, *args, **options):
        if options['confidential']:
            self.filters['type'] = 'confidential'

        if options['public']:
            self.filters['type'] = 'public'

        if options['trusted']:
            self.filters['is_trusted'] = True
