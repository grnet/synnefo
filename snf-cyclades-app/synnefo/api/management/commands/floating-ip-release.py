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

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError

from synnefo.management.common import get_floating_ip_by_address
from synnefo import quotas

class Command(BaseCommand):
    can_import_settings = True
    output_transaction = True

    help = "Release a floating IP"

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if not args:
            raise CommandError("Please provide a floating-ip address")

        address = args[0]

        floating_ip = get_floating_ip_by_address(address, for_update=True)
        if floating_ip.nic:
            # This is safe, you also need for_update to attach floating IP to
            # instance.
            msg = "Floating IP '%s' is attached to instance." % floating_ip.id
            raise CommandError(msg)

        # Return the address of the floating IP back to pool
        floating_ip.release_address()
        # And mark the floating IP as deleted
        floating_ip.deleted = True
        floating_ip.save()
        # Release quota for floating IP
        quotas.issue_and_accept_commission(floating_ip, delete=True)
        transaction.commit()
        # Delete the floating IP from DB
        floating_ip.delete()

        self.stdout.write("Deleted floating IP '%s'.\n" % address)
