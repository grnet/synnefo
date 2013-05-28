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

from django.core.management.base import CommandError
from astakos.im.models import Service
from synnefo.lib.ordereddict import OrderedDict
from synnefo.webproject.management.commands import SynnefoCommand
from synnefo.webproject.management import utils


class Command(SynnefoCommand):
    args = "<service name or ID>"
    help = "Show service details"

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a service name or ID.")

        identifier = args[0]
        if identifier.isdigit():
            try:
                service = Service.objects.get(id=int(identifier))
            except Service.DoesNotExist:
                raise CommandError('No service found with ID %s.' % identifier)
        else:
            try:
                service = Service.objects.get(name=identifier)
            except Service.DoesNotExist:
                raise CommandError('No service found named %s.' % identifier)

        kv = OrderedDict(
            [
                ('id', service.id),
                ('name', service.name),
                ('type', service.type),
                ('service URL', service.url),
                ('API URL', service.api_url),
                ('token', service.auth_token),
                ('token created', service.auth_token_created),
                ('token expires', service.auth_token_expires),
            ])

        utils.pprint_table(self.stdout, [kv.values()], kv.keys(),
                           options["output_format"], vertical=True)
