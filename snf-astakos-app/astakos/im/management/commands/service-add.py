# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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
from django.db.utils import IntegrityError

from astakos.im.models import Service


class Command(BaseCommand):
    args = "<name> <service URL> <API URL> "
    help = "Register a service"

    option_list = BaseCommand.option_list + (
        make_option('--type',
                    dest='type',
                    help="Service type"),
    )

    def handle(self, *args, **options):
        if len(args) < 2:
            raise CommandError("Invalid number of arguments")

        name = args[0]
        url = args[1]
        api_url = args[2]
        kwargs = dict(name=name, url=url, api_url=api_url)
        if options['type']:
            kwargs['type'] = options['type']

        try:
            s = Service.objects.get(name=name)
            m = "There already exists service named '%s'." % name
            raise CommandError(m)
        except Service.DoesNotExist:
            pass

        services = list(Service.objects.filter(url=url))
        if services:
            m = "Service URL '%s' is registered for another service." % url
            raise CommandError(m)

        services = list(Service.objects.filter(api_url=api_url))
        if services:
            m = "API URL '%s' is registered for another service." % api_url
            raise CommandError(m)

        try:
            s = Service.objects.create(**kwargs)
        except BaseException:
            raise CommandError("Failed to create service.")
        else:
            self.stdout.write('Token: %s\n' % s.auth_token)
