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

from django.core.management.base import BaseCommand
from optparse import make_option


from synnefo import quotas
from synnefo.quotas.util import (get_db_holdings, get_quotaholder_holdings,
                                 transform_quotas)
from synnefo.webproject.management.utils import pprint_table
from synnefo.settings import CYCLADES_ASTAKOS_SERVICE_TOKEN as ASTAKOS_TOKEN


class Command(BaseCommand):
    help = """Reconcile resource usage of Astakos with Cyclades DB.

    Detect unsynchronized usage between Astakos and Cyclades DB resources and
    synchronize them if specified so.

    """
    option_list = BaseCommand.option_list + (
        make_option("--userid", dest="userid",
                    default=None,
                    help="Reconcile resources only for this user"),
        make_option("--fix", dest="fix",
                    default=False,
                    action="store_true",
                    help="Synchronize Astakos quotas with Cyclades DB."),
        make_option("--force",
                    default=False,
                    action="store_true",
                    help="Override Astakos quotas. Force Astakos to impose"
                         " the Cyclades quota, independently of their value.")
    )

    def handle(self, *args, **options):
        write = self.stdout.write
        userid = options['userid']

        # Get holdings from Cyclades DB
        db_holdings = get_db_holdings(userid)
        # Get holdings from QuotaHolder
        qh_holdings = get_quotaholder_holdings(userid)

        users = set(db_holdings.keys())
        users.update(qh_holdings.keys())
        # Remove 'None' user
        users.discard(None)

        if userid and userid not in users:
            write("User '%s' does not exist in Quotaholder!", userid)
            return

        unsynced = []
        for user in users:
            db = db_holdings.get(user, {})
            try:
                qh_all = qh_holdings[user]
            except KeyError:
                write("User '%s' does not exist in Quotaholder!\n" %
                      user)
                continue

            # Assuming only one source
            qh = qh_all.get(quotas.DEFAULT_SOURCE, {})
            qh = transform_quotas(qh)
            for resource in quotas.RESOURCES:
                db_value = db.pop(resource, 0)
                try:
                    qh_value, _, qh_pending = qh[resource]
                except KeyError:
                    write("Resource '%s' does not exist in Quotaholder"
                          " for user '%s'!\n" % (resource, user))
                    continue
                if qh_pending:
                    write("Pending commission. User '%s', resource '%s'.\n" %
                          (user, resource))
                    continue
                if db_value != qh_value:
                    data = (user, resource, db_value, qh_value)
                    unsynced.append(data)

        headers = ("User", "Resource", "Database", "Quotaholder")
        if unsynced:
            pprint_table(self.stderr, unsynced, headers)
            if options["fix"]:
                qh = quotas.Quotaholder.get()
                request = {}
                request["force"] = options["force"]
                request["auto_accept"] = True
                request["provisions"] = map(create_provision, unsynced)
                qh.issue_commission(ASTAKOS_TOKEN, request)
        else:
            write("Everything in sync.\n")


def create_provision(provision_info):
    user, resource, db_value, qh_value = provision_info
    return {"holder": user,
            "source": quotas.DEFAULT_SOURCE,
            "resource": resource,
            "quantity": db_value - qh_value}
