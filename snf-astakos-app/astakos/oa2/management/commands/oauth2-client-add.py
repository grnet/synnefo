# Copyright 2013-2014 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

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
