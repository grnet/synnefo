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

from django.core.management.base import BaseCommand
from optparse import make_option

from synnefo.quotas import get_quota_holder
from synnefo.quotas.util import get_db_holdings


class Command(BaseCommand):
    help = """Reset cyclades.* usage values in Quotaholder"""
    output_transaction = True
    option_list = BaseCommand.option_list + (
        make_option("--userid", dest="userid",
                    default=None,
                    help="Verify quotas only for this user"),
        make_option("--dry-run", dest="dry_run",
                    action='store_true',
                    default=False),
    )

    def handle(self, *args, **options):
        userid = options['userid']

        users = [userid] if userid else None
        # Get info from DB
        db_holdings = get_db_holdings(users)

        # Create commissions
        with get_quota_holder() as qh:
            for user, resources in db_holdings.items():
                if not user:
                    continue
                reset_holding = []
                for res, val in resources.items():
                    reset_holding.append((user, "cyclades." + res, "1", val, 0,
                                          0, 0))
                if not options['dry_run']:
                    try:
                        qh.reset_holding(context={},
                                         reset_holding=reset_holding)
                    except Exception as e:
                        self.stderr.write("Can not set up holding:%s" % e)
                else:
                    self.stdout.write("Reseting holding: %s\n" % reset_holding)
