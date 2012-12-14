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

from synnefo.quotas.util import get_db_holdings, get_quotaholder_holdings
from synnefo.management.common import pprint_table


class Command(BaseCommand):
    output_transaction = True
    option_list = BaseCommand.option_list + (
        make_option("--userid", dest="userid",
                    default=None,
                    help="Verify quotas only for this user"),
    )

    def handle(self, *args, **options):
        write = self.stdout.write
        userid = options['userid']

        users = [userid] if userid else None
        # Get info from DB
        db_holdings = get_db_holdings(users)
        users = db_holdings.keys()
        qh_holdings = get_quotaholder_holdings(users)
        qh_users = qh_holdings.keys()

        if len(qh_users) < len(users):
            for u in set(users) - set(qh_users):
                write("Unknown entity: %s\n" % u)
                users = qh_users

        headers = ("User", "Resource", "Database", "Quotaholder")
        unsynced = []
        for user in users:
            db = db_holdings[user]
            qh = qh_holdings[user]
            if not self.verify_resources(user, db.keys(), qh.keys()):
                continue

            for res in db.keys():
                if db[res] != qh[res]:
                    unsynced.append((user, res, str(db[res]), str(qh[res])))

        if unsynced:
            pprint_table(self.stderr, unsynced, headers)

    def verify_resources(self, user, db_resources, qh_resources):
        write = self.stderr.write
        db_res = set(db_resources)
        qh_res = set(qh_resources)
        if qh_res == db_res:
            return True
        db_extra = db_res - qh_res
        if db_extra:
            for res in db_extra:
                write("Resource %s exists in DB for %s but not in QH\n"\
                      % (res, user))
        qh_extra = qh_res - db_res
        if qh_extra:
            for res in qh_extra:
                write("Resource %s exists in QH for %s but not in DB\n"\
                      % (res, user))
        return False
