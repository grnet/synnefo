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

from snf_django.management.commands import SynnefoCommand, CommandError
from astakos.im.user_logic import send_verification_mail

from ._common import get_user


class Command(SynnefoCommand):
    args = "<user ID or email> [user ID or email] ..."
    help = "Sends an activation email to one or more users"

    def handle(self, *args, **options):
        if not args:
            raise CommandError("No user was given")

        for email_or_id in args:
            user = get_user(email_or_id)
            if not user:
                self.stderr.write("Unknown user '%s'\n" % (email_or_id,))
                continue
            if user.email_verified:
                self.stderr.write(
                    "User email already verified '%s'\n" % (user.email,))
                continue

            send_verification_mail(user)

            self.stderr.write("Activation sent to '%s'\n" % (user.email,))
