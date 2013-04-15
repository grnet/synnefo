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

from django.core.management.base import NoArgsCommand, CommandError

from pithos.api.util import get_backend

import logging

logger = logging.getLogger(__name__)

class Command(NoArgsCommand):
    help = "Display unresolved commissions and trigger their recovery"

    def handle_noargs(self, **options):
        b = get_backend()
        try:
            pending_commissions = b.quotaholder.get_pending_commissions()

            to_accept = b.quotaholder_serials.lookup(pending_commissions)
            self.stdout.write("Accept commissions: %s\n" %  to_accept)
            b.quotaholder.accept_commission(
                context     =   {},
                clientkey   =   'pithos',
                serials     =   to_accept
            )
            self.stdout.write("Delete serials: %s\n" %  to_accept)
            b.quotaholder_serials.delete_many(to_accept)

            to_reject = list(set(pending_commissions) - set(to_accept))
            self.stdout.write("Reject commissions: %s\n" %  to_reject)
            b.quotaholder.reject_commission(
                context     =   {},
                clientkey   =   'pithos',
                serials     =   to_reject
            )

        except Exception, e:
            logger.exception(e)
            raise CommandError(e)
        finally:
            b.close()
