# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
from optparse import make_option

from synnefo import quotas
from synnefo.quotas import util
from synnefo.quotas import errors
from snf_django.management.utils import pprint_table
from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.utils import reconcile


class Command(SynnefoCommand):
    help = """Reconcile resource usage of Astakos with Cyclades DB.

    Detect unsynchronized usage between Astakos and Cyclades DB resources and
    synchronize them if specified so.

    """
    option_list = SynnefoCommand.option_list + (
        make_option("--user", dest="userid",
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
        db_holdings = util.get_db_holdings(user=userid, project=project)
        db_project_holdings = util.get_db_holdings(project=project,
                                                   for_users=False)

        # Get holdings from QuotaHolder
        try:
            qh_holdings = util.get_qh_users_holdings(
                [userid] if userid is not None else None,
                [project] if project is not None else None)
            qh_project_holdings = util.get_qh_project_holdings(
                [project] if project is not None else None)
        except errors.AstakosClientException as e:
            raise CommandError(e)

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
