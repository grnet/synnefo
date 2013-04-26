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

from django.core.management.base import BaseCommand
from optparse import make_option

from synnefo import quotas


class Command(BaseCommand):
    help = "Detect and resolve pending commissions to Quotaholder"
    output_transaction = True
    option_list = BaseCommand.option_list + (
        make_option("--fix", dest="fix",
                    action='store_true',
                    default=False,
                    help="Fix pending commissions"
                    ),
    )

    def handle(self, *args, **options):
        fix = options['fix']

        accepted, rejected = quotas.resolve_pending_commissions()

        if accepted:
            self.stdout.write("Pending accepted commissions:\n %s\n"
                              % list_to_string(accepted))

        if rejected:
            self.stdout.write("Pending rejected commissions:\n %s\n"
                              % list_to_string(rejected))

        if fix and (accepted or rejected):
            self.stdout.write("Fixing pending commissions..\n")
            quotas.resolve_commissions(accepted=accepted, rejected=rejected,
                                       strict=False)


def list_to_string(l):
    return ",".join([str(x) for x in l])
