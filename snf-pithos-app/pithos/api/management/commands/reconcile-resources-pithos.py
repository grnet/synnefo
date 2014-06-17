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
from django.core.management.base import CommandError

from optparse import make_option

from pithos.api.util import get_backend

from snf_django.management import utils

from snf_django.management.commands import SynnefoCommand
from astakosclient.errors import QuotaLimit, NotFound
from snf_django.utils import reconcile

backend = get_backend()
RESOURCES = ['pithos.diskspace']


class Command(SynnefoCommand):
    help = """Reconcile resource usage of Astakos with Pithos DB.

    Detect unsynchronized usage between Astakos and Pithos DB resources and
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
                    help="Synchronize Astakos quotas with Pithos DB."),
        make_option("--force",
                    default=False,
                    action="store_true",
                    help="Override Astakos quotas. Force Astakos to impose "
                         "the Pithos quota, independently of their value.")
    )

    def handle(self, **options):
        write = self.stdout.write
        try:
            backend.pre_exec()
            userid = options['userid']
            project = options['project']

            # Get holding from Pithos DB
            db_usage = backend.node.node_account_usage(userid, project)
            db_project_usage = backend.node.node_project_usage(project)

            users = set(db_usage.keys())
            if userid and userid not in users:
                if backend._lookup_account(userid) is None:
                    write("User '%s' does not exist in DB!\n" % userid)
                    return

            # Get holding from Quotaholder
            try:
                qh_result = backend.astakosclient.service_get_quotas(userid)
            except NotFound:
                write("User '%s' does not exist in Quotaholder!\n" % userid)
                return

            try:
                qh_project_result = \
                    backend.astakosclient.service_get_project_quotas(project)
            except NotFound:
                write("Project '%s' does not exist in Quotaholder!\n" %
                      project)

            unsynced_users, users_pending, users_unknown =\
                reconcile.check_users(self.stderr, RESOURCES,
                                      db_usage, qh_result)

            unsynced_projects, projects_pending, projects_unknown =\
                reconcile.check_projects(self.stderr, RESOURCES,
                                         db_project_usage, qh_project_result)
            pending_exists = users_pending or projects_pending
            unknown_exists = users_unknown or projects_unknown

            headers = ("Type", "Holder", "Source", "Resource",
                       "Database", "Quotaholder")
            unsynced = unsynced_users + unsynced_projects
            if unsynced:
                utils.pprint_table(self.stdout, unsynced, headers)
                if options["fix"]:
                    force = options["force"]
                    name = ("client: reconcile-resources-pithos, time: %s"
                            % datetime.now())
                    user_provisions = reconcile.create_user_provisions(
                        unsynced_users)
                    project_provisions = reconcile.create_project_provisions(
                        unsynced_projects)
                    try:
                        backend.astakosclient.issue_commission_generic(
                            user_provisions, project_provisions, name=name,
                            force=force, auto_accept=True)
                    except QuotaLimit:
                        write("Reconciling failed because a limit has been "
                              "reached. Use --force to ignore the check.\n")
                        return
                    write("Fixed unsynced resources\n")

            if pending_exists:
                write("Found pending commissions. Run 'snf-manage"
                      " reconcile-commissions-pithos'\n")
            elif not (unsynced or unknown_exists):
                write("Everything in sync.\n")
        except BaseException as e:
            backend.post_exec(False)
            raise CommandError(e)
        else:
            backend.post_exec(True)
        finally:
            backend.close()
