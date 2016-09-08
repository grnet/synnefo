# Copyright (C) 2010-2016 GRNET S.A.
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

import string
from datetime import datetime

from optparse import make_option

from astakos.im import transaction
from snf_django.management.commands import SynnefoCommand, CommandError

from astakos.im.models import AstakosUser
from astakos.im import functions, activation_backends
from django.conf import settings

SUSPENSION_REASON = activation_backends.PROJECT_SUSPENSION_REASON


class Command(SynnefoCommand):
    help = "Check and fix user state"
    args = "<user ID> (or --all-users)"

    option_list = SynnefoCommand.option_list + (
        make_option('--suspend-deactivated',
                    action="store_true",
                    default=False,
                    help="Suspend projects if user is deactivated"),
        make_option('--all-users',
                    action="store_true",
                    default=False,
                    help="Perform action on all users"),
        make_option('--fix',
                    action="store_true",
                    default=False,
                    help="Apply actions"),
        make_option('--noemail',
                    action="store_true",
                    default=False,
                    help="Don't send email to affected users"),
    )

    def get_user(self, query, userid):
        if userid.isdigit():
            try:
                return query.get(id=int(userid))
            except AstakosUser.DoesNotExist:
                raise CommandError("Invalid user ID")
        elif is_uuid(userid):
            try:
                return query.get(uuid=userid)
            except AstakosUser.DoesNotExist:
                raise CommandError("Invalid user UUID")
        else:
            raise CommandError(("Invalid user identification: "
                                "you should provide a valid user ID "
                                "or a valid user UUID"))

    def handle(self, *args, **options):
        if options["noemail"]:
            settings.EMAIL_BACKEND = \
                "django.core.mail.backends.dummy.EmailBackend"

        fix = options["fix"]
        all_users = options["all_users"]
        if not (all_users ^ bool(args)):
            raise CommandError("Need to specify either a userid "
                               "or option --all-users.")
        userid = None if all_users else args[0]
        if options["suspend_deactivated"]:
            self.suspend_projects(userid, fix)
        else:
            self.stderr.write("No action specified.\n")

    @transaction.commit_on_success
    def suspend_projects(self, userid, fix):
        count = 0
        deactivated = AstakosUser.objects.accepted().filter(
            is_active=False).select_for_update()
        if userid is None:
            users = deactivated
        else:
            users = [self.get_user(deactivated, userid)]

        affected_users = functions.suspend_users_projects(
            users, reason=SUSPENSION_REASON, fix=fix)
        if affected_users:
            verb = "Suspended" if fix else "Would suspend"
            self.stderr.write(
                "%s projects/memberships for %s "
                "deactivated users:\n" % (verb, len(affected_users)))
            for user in affected_users:
                self.stderr.write("%s (%s)\n" % (user.email, user.uuid))
        else:
            self.stderr.write("No users affected.\n")
