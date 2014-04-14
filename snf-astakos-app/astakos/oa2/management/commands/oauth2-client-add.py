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

from django.db import transaction

from snf_django.management.commands import SynnefoCommand, CommandError

from astakos.oa2.models import Client, RedirectUrl
from astakos.oa2 import settings


class Command(SynnefoCommand):
    args = "<identfier>"
    help = "Create an oauth2 client"

    option_list = SynnefoCommand.option_list + (
        make_option('--secret',
                    dest='secret',
                    metavar='SECRET',
                    action='store',
                    default=None,
                    help="Set client's secret"),
        make_option('--is-trusted',
                    action='store_true',
                    dest='is_trusted',
                    default=False,
                    help="Whether client is trusted or not"),
        make_option('--type',
                    action='store',
                    dest='type',
                    default='confidential',
                    help="Set client's type"),
        make_option('--url',
                    action='append',
                    dest='urls',
                    default=[],
                    help="Set client's redirect URLs"),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Invalid number of arguments")

        urls = filter(lambda u: len(u) <
                      settings.MAXIMUM_ALLOWED_REDIRECT_URI_LENGTH,
                      options['urls'])

        if len(options['urls']) != len(urls):
            self.stdout.write('The following urls are over the allowed limit '
                              'and are going to be ignored: %s\n' %
                              ','.join(set(options['urls']) - set(urls)))

        if not urls:
            raise CommandError("There should be at least one redirect URI")

        identifier = args[0].decode('utf8')

        try:
            c = Client(identifier=identifier, secret=options['secret'],
                       type=options['type'], is_trusted=options['is_trusted'])
            c.save()
            c.redirecturl_set.bulk_create((RedirectUrl(client=c, url=url) for
                                          url in urls))
            c.save()

        except BaseException, e:
            raise CommandError(e)
        else:
            self.stdout.write('Client created successfully\n')
