# Copyright 2012 GRNET S.A. All rights reserved.
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

from django.core.management.base import BaseCommand, CommandError

from astakos.im.models import Component


class Command(BaseCommand):
    args = "<component ID or name>"
    help = "Modify component attributes"

    option_list = BaseCommand.option_list + (
        make_option('--url',
                    dest='url',
                    default=None,
                    help="Set component url"),
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

        url = options.get('url')
        auth_token = options.get('auth_token')
        renew_token = options.get('renew_token')
        purge_services = options.get('purge_services')

        if not any([url, auth_token, renew_token, purge_services]):
            raise CommandError("No option specified.")


        if url:
            component.url = url

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
