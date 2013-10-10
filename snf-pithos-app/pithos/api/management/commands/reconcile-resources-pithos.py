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
from django.core.management.base import NoArgsCommand, CommandError

from optparse import make_option

from pithos.api.util import get_backend

from snf_django.management import utils

from astakosclient.errors import QuotaLimit, NotFound
from snf_django.utils import reconcile

backend = get_backend()
RESOURCES = ['pithos.diskspace']


class Command(NoArgsCommand):
    help = """Reconcile resource usage of Astakos with Pithos DB.

    Detect unsynchronized usage between Astakos and Pithos DB resources and
    synchronize them if specified so.

    """
    option_list = NoArgsCommand.option_list + (
        make_option("--userid", dest="userid",
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

    def handle_noargs(self, **options):
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
