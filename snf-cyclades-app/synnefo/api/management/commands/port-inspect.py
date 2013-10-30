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
from django.core.management.base import BaseCommand, CommandError

from synnefo.management.common import convert_api_faults
from synnefo.api.util import get_port
from synnefo.management import pprint


class Command(BaseCommand):
    help = "Inspect a port on DB and Ganeti"
    args = "<port ID>"

    option_list = BaseCommand.option_list + (
        make_option(
            '--jobs',
            action='store_true',
            dest='jobs',
            default=False,
            help="Show non-archived jobs concerning port."),
        make_option(
            '--displayname',
            action='store_true',
            dest='displayname',
            default=False,
            help="Display both uuid and display name"),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a port ID")

        port = get_port(args[0], None)

        pprint.pprint_port(port, stdout=self.stdout)
        self.stdout.write('\n\n')

        pprint.pprint_port_ips(port, stdout=self.stdout)
        self.stdout.write('\n\n')

        pprint.pprint_port_in_ganeti(port, stdout=self.stdout)
