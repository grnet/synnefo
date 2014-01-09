# Copyright 2013 GRNET S.A. All rights reserved.
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
