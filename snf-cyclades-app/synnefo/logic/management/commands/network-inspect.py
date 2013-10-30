# Copyright 2012-2013 GRNET S.A. All rights reserved.
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
from synnefo.management import pprint, common


class Command(BaseCommand):
    help = "Inspect a network on DB and Ganeti."

    option_list = BaseCommand.option_list + (
        make_option(
            '--displayname',
            action='store_true',
            dest='displayname',
            default=False,
            help="Display both uuid and display name"),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a network ID.")

        network = common.get_network(args[0])
        displayname = options['displayname']

        pprint.pprint_network(network, display_mails=displayname,
                              stdout=self.stdout)
        self.stdout.write("\n\n")
        pprint.pprint_network_subnets(network, stdout=self.stdout)
        self.stdout.write("\n\n")
        pprint.pprint_network_backends(network, stdout=self.stdout)
        self.stdout.write("\n\n")
        pprint.pprint_network_in_ganeti(network, stdout=self.stdout)
