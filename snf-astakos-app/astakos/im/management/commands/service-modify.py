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

from astakos.im.models import Service


class Command(BaseCommand):
    args = "<service ID>"
    help = "Modify service attributes"

    option_list = BaseCommand.option_list + (
        make_option('--order',
                    dest='order',
                    metavar='NUM',
                    default=None,
                    help="Set service order"),
        make_option('--name',
                    dest='name',
                    default=None,
                    help="Set service name"),
        make_option('--url',
                    dest='url',
                    default=None,
                    help="Set service url"),
        make_option('--icon',
                    dest='icon',
                    default=None,
                    help="Set service icon (displayed by cloudbar)"),
        make_option('--token',
                    dest='auth_token',
                    default=None,
                    help="Set a custom service auth token"),
        make_option('--renew-token',
                    action='store_true',
                    dest='renew_token',
                    default=False,
                    help="Renew service auth token"),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a service ID")

        try:
            service = Service.objects.get(id=int(args[0]))
        except Service.DoesNotExist:
            raise CommandError("Service does not exist. You may run snf-mange "
                               "service-list for available service IDs.")

        order = options.get('order')
        name = options.get('name')
        url = options.get('url')
        icon = options.get('icon')
        auth_token = options.get('auth_token')
        renew_token = options.get('renew_token')

        if order is not None:
            service.order = order

        if name:
            service.name = name

        if url:
            service.url = url

        if icon:
            service.icon = icon

        if auth_token:
            service.auth_token = auth_token

        if renew_token and not auth_token:
            service.renew_token()

        service.save()

        if renew_token:
            self.stdout.write(
                'Service\'s new token: %s\n' % service.auth_token
            )
