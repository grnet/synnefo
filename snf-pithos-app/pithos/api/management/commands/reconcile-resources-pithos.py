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

from django.core.management.base import NoArgsCommand

from optparse import make_option

from pithos.api.util import get_backend
from pithos.api.resources import resources
from pithos.backends.modular import DEFAULT_SOURCE

from snf_django.management import utils

from astakosclient.errors import QuotaLimit, NotFound

backend = get_backend()


class Command(NoArgsCommand):
    help = """Reconcile resource usage of Astakos with Pithos DB.

    Detect unsynchronized usage between Astakos and Pithos DB resources and
    synchronize them if specified so.

    """
    option_list = NoArgsCommand.option_list + (
        make_option("--userid", dest="userid",
                    default=None,
                    help="Reconcile resources only for this user"),
        make_option("--fix", dest="fix",
                    default=False,
                    action="store_true",
                    help="Synchronize Astakos quotas with Pithos DB."),
        make_option("--force",
                    default=False,
                    action="store_true",
                    help="Override Astakos quotas. Force Astakos to impose "
                         "the Pithos quota, independently of their value.")
    )

    def handle_noargs(self, **options):
        try:
            backend.pre_exec()
            userid = options['userid']

            # Get holding from Pithos DB
            db_usage = backend.node.node_account_usage(userid)

            users = set(db_usage.keys())
            if userid and userid not in users:
                if backend._lookup_account(userid) is None:
                    self.stdout.write("User '%s' does not exist in DB!\n" %
                                      userid)
                    return

            # Get holding from Quotaholder
            try:
                qh_result = backend.astakosclient.service_get_quotas(userid)
            except NotFound:
                self.stdout.write(
                    "User '%s' does not exist in Quotaholder!\n" % userid)
                return

            users.update(qh_result.keys())

            pending_exists = False
            unknown_user_exists = False
            unsynced = []
            for uuid in users:
                db_value = db_usage.get(uuid, 0)
                try:
                    qh_all = qh_result[uuid]
                except KeyError:
                    self.stdout.write(
                        "User '%s' does not exist in Quotaholder!\n" % uuid)
                    unknown_user_exists = True
                    continue
                else:
                    qh = qh_all.get(DEFAULT_SOURCE, {})
                    for resource in [r['name'] for r in resources]:
                        try:
                            qh_resource = qh[resource]
                        except KeyError:
                            self.stdout.write(
                                "Resource '%s' does not exist in Quotaholder "
                                "for user '%s'!\n" % (resource, uuid))
                            continue

                        if qh_resource['pending']:
                            self.stdout.write(
                                "Pending commission. "
                                "User '%s', resource '%s'.\n" %
                                (uuid, resource))
                            pending_exists = True
                            continue

                        qh_value = qh_resource['usage']

                        if db_value != qh_value:
                            data = (uuid, resource, db_value, qh_value)
                            unsynced.append(data)

            if unsynced:
                headers = ("User", "Resource", "Database", "Quotaholder")
                utils.pprint_table(self.stdout, unsynced, headers)
                if options['fix']:
                    request = {}
                    request['force'] = options['force']
                    request['auto_accept'] = True
                    request['name'] = "RECONCILE"
                    request['provisions'] = map(create_provision, unsynced)
                    try:
                        backend.astakosclient.issue_commission(request)
                    except QuotaLimit:
                        self.stdout.write(
                            "Reconciling failed because a limit has been "
                            "reached. Use --force to ignore the check.\n")
                        return
                    self.stdout.write("Fixed unsynced resources\n")

            if pending_exists:
                self.stdout.write(
                    "Found pending commissions. Run 'snf-manage"
                    " reconcile-commissions-pithos'\n")
            elif not (unsynced or unknown_user_exists):
                self.stdout.write("Everything in sync.\n")
        except BaseException as e:
            backend.post_exec(False)
            self.stdout.write(str(e) + "\n")
        else:
            backend.post_exec(True)
        finally:
            backend.close()


def create_provision(provision_info):
    user, resource, db_value, qh_value = provision_info
    return {"holder": user,
            "source": DEFAULT_SOURCE,
            "resource": resource,
            "quantity": int(db_value - qh_value)}
