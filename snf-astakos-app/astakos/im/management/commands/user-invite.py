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

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError
from django.db import transaction

from astakos.im.functions import SendMailError
from astakos.im.models import Invitation

from ._common import get_user


@transaction.commit_manually
class Command(BaseCommand):
    args = "<inviter id or email> <email> <real name>"
    help = "Invite a user"

    def handle(self, *args, **options):
        if len(args) != 3:
            raise CommandError("Invalid number of arguments")

        inviter = get_user(args[0], is_active=True)
        if not inviter:
            raise CommandError("Unknown inviter")
        if not inviter.is_active:
            raise CommandError("Inactive inviter")

        if inviter.invitations > 0:
            email = args[1]
            realname = args[2]

            try:
                inviter.invite(email, realname)
                self.stdout.write("Invitation sent to '%s'\n" % (email,))
            except SendMailError, e:
                transaction.rollback()
                raise CommandError(e.message)
            except IntegrityError, e:
                transaction.rollback()
                raise CommandError(
                    "There is already an invitation for %s" % (email,))
            else:
                transaction.commit()
        else:
            raise CommandError("No invitations left")
