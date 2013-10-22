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
from synnefo.management.common import convert_api_faults

from synnefo.api import util
from synnefo.management.common import get_network, get_vm
from synnefo.logic import servers


class Command(BaseCommand):
    can_import_settings = True
    output_transaction = True

    help = "Attach a floating IP to a VM or router"

    option_list = BaseCommand.option_list + (
        make_option(
            '--machine',
            dest='machine',
            default=None,
            help='The server id the floating-ip will be attached to'),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if not args or len(args) > 1:
            raise CommandError("Command accepts exactly one argument")

        floating_ip = args[0]  # this is the floating-ip address
        device = options['machine']

        if not device:
            raise CommandError('Please give either a server or a router id')

        #get the vm
        vm = get_vm(device)

        servers.add_floating_ip(vm, floating_ip)

        self.stdout.write("Attached %s to %s.\n" % (floating_ip, vm))
