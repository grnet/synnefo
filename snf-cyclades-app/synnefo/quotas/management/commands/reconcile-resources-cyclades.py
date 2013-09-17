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

from datetime import datetime
from django.core.management.base import BaseCommand
from optparse import make_option

from synnefo import quotas
from synnefo.quotas import util
from snf_django.management.utils import pprint_table
from snf_django.utils import reconcile


class Command(BaseCommand):
    help = """Reconcile resource usage of Astakos with Cyclades DB.

    Detect unsynchronized usage between Astakos and Cyclades DB resources and
    synchronize them if specified so.

    """
    option_list = BaseCommand.option_list + (
        make_option("--userid", dest="userid",
                    default=None,
                    help="Reconcile resources only for this user"),
        make_option("--project",
                    help="Reconcile resources only for this project"),
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
        write = self.stderr.write
        userid = options['userid']
        project = options["project"]

        # Get holdings from Cyclades DB
        db_holdings = util.get_db_holdings(userid, project)
        db_project_holdings = util.get_db_project_holdings(project)

        # Get holdings from QuotaHolder
        qh_holdings = util.get_qh_users_holdings(
            [userid] if userid is not None else None)
        qh_project_holdings = util.get_qh_project_holdings(
            [project] if project is not None else None)

        unsynced_users, users_pending, users_unknown =\
            reconcile.check_users(self.stderr, quotas.RESOURCES,
                                  db_holdings, qh_holdings)

        unsynced_projects, projects_pending, projects_unknown =\
            reconcile.check_projects(self.stderr, quotas.RESOURCES,
                                     db_project_holdings, qh_project_holdings)
        pending_exists = users_pending or projects_pending
        unknown_exists = users_unknown or projects_unknown

        headers = ("Type", "Holder", "Source", "Resource",
                   "Database", "Quotaholder")
        unsynced = unsynced_users + unsynced_projects
        if unsynced:
            pprint_table(self.stdout, unsynced, headers)
            if options["fix"]:
                qh = quotas.Quotaholder.get()
                force = options["force"]
                name = ("client: reconcile-resources-cyclades, time: %s"
                        % datetime.now())
                user_provisions = reconcile.create_user_provisions(
                    unsynced_users)
                project_provisions = reconcile.create_project_provisions(
                    unsynced_projects)
                try:
                    qh.issue_commission_generic(
                        user_provisions, project_provisions,
                        name=name, force=force,
                        auto_accept=True)
                except quotas.errors.QuotaLimit:
                    write("Reconciling failed because a limit has been "
                          "reached. Use --force to ignore the check.\n")
                    return
                write("Fixed unsynced resources\n")

        if pending_exists:
            write("Found pending commissions. Run 'snf-manage"
                  " reconcile-commissions-cyclades'\n")
        elif not (unsynced or unknown_exists):
            write("Everything in sync.\n")
