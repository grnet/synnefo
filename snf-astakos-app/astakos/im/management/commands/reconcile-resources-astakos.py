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

from synnefo.webproject.management.utils import pprint_table
from snf_django.lib.db.transaction import commit_on_success_strict
from astakos.im.models import Service, AstakosUser
from astakos.im.quotas import service_get_quotas, SYSTEM
from astakos.im.functions import count_pending_app
import astakos.quotaholder_app.callpoint as qh
import astakos.quotaholder_app.exception as qh_exception


class Command(BaseCommand):
    help = """Reconcile resource usage of Quotaholder with Astakos DB.

    Detect unsynchronized usage between Quotaholder and Astakos DB resources
    and synchronize them if specified so.

    """

    option_list = BaseCommand.option_list + (
        make_option("--userid", dest="userid",
                    default=None,
                    help="Reconcile resources only for this user"),
        make_option("--fix", dest="fix",
                    default=False,
                    action="store_true",
                    help="Synchronize Quotaholder with Astakos DB."),
        make_option("--force",
                    default=False,
                    action="store_true",
                    help="Override Quotaholder. Force Quotaholder to impose"
                         " the quota, independently of their value.")
    )

    @commit_on_success_strict()
    def handle(self, *args, **options):
        write = self.stdout.write
        force = options['force']
        userid = options['userid']

        try:
            astakos = Service.objects.get(name="astakos")
        except Service.DoesNotExist:
            raise CommandError("Service 'astakos' not found.")

        query = [userid] if userid is not None else None
        qh_holdings = service_get_quotas(astakos, query)

        if userid is None:
            users = AstakosUser.objects.verified()
        else:
            try:
                users = [AstakosUser.objects.get(uuid=userid)]
            except AstakosUser.DoesNotExist:
                raise CommandError("There is no user with uuid '%s'." % userid)

        db_holdings = count_pending_app(users)

        pending_exists = False
        unknown_user_exists = False
        unsynced = []
        for user in users:
            uuid = user.uuid
            db_value = db_holdings.get(uuid, 0)
            try:
                qh_all = qh_holdings[uuid]
            except KeyError:
                write("User '%s' does not exist in Quotaholder!\n" % uuid)
                unknown_user_exists = True
                continue

            # Assuming only one source
            system_qh = qh_all.get(SYSTEM, {})
            # Assuming only one resource
            resource = 'astakos.pending_app'
            try:
                qh_values = system_qh[resource]
                qh_value = qh_values['usage']
                qh_pending = qh_values['pending']
            except KeyError:
                write("Resource '%s' does not exist in Quotaholder"
                      " for user '%s'!\n" % (resource, uuid))
                continue
            if qh_pending:
                write("Pending commission. User '%s', resource '%s'.\n" %
                      (uuid, resource))
                pending_exists = True
                continue
            if db_value != qh_value:
                data = (uuid, resource, db_value, qh_value)
                unsynced.append(data)

        headers = ("User", "Resource", "Astakos", "Quotaholder")
        if unsynced:
            pprint_table(self.stderr, unsynced, headers)
            if options["fix"]:
                provisions = map(create_provision, unsynced)
                try:
                    s = qh.issue_commission('astakos', provisions,
                                            name='RECONCILE', force=force)
                except qh_exception.NoCapacityError:
                    write("Reconciling failed because a limit has been "
                          "reached. Use --force to ignore the check.\n")
                    return

                qh.resolve_pending_commission('astakos', s)
                write("Fixed unsynced resources\n")

        if pending_exists:
            write("Found pending commissions. "
                  "This is probably a bug. Please report.\n")
        elif not (unsynced or unknown_user_exists):
            write("Everything in sync.\n")


def create_provision(provision_info):
    user, resource, db_value, qh_value = provision_info
    return (user, SYSTEM, resource), (db_value - qh_value)
