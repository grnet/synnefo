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

from optparse import make_option
from django.db import transaction

from astakos.im.models import AstakosUser
from astakos.im.quotas import (
    qh_sync_users_diffs,)
from astakos.im.functions import get_user_by_uuid
from snf_django.management.commands import SynnefoCommand
from astakos.im.management.commands import _common as common

import logging
logger = logging.getLogger(__name__)


class Command(SynnefoCommand):
    help = "Check the integrity of user quota"

    option_list = SynnefoCommand.option_list + (
        make_option('--sync',
                    action='store_true',
                    dest='sync',
                    default=False,
                    help="Sync quotaholder"),
        make_option('--user',
                    metavar='<uuid or email>',
                    dest='user',
                    help="Check for a specified user"),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        sync = options['sync']
        user_ident = options['user']

        if user_ident is not None:
            users = [common.get_accepted_user(user_ident)]
        else:
            users = AstakosUser.objects.accepted()

        qh_limits, diff_q = qh_sync_users_diffs(users, sync=sync)
        if sync:
            self.print_sync(diff_q)
        else:
            self.print_verify(qh_limits, diff_q)

    def print_sync(self, diff_quotas):
        size = len(diff_quotas)
        if size == 0:
            self.stderr.write("No sync needed.\n")
        else:
            self.stderr.write("Synced %s users:\n" % size)
            uuids = diff_quotas.keys()
            users = AstakosUser.objects.filter(uuid__in=uuids)
            for user in users:
                self.stderr.write("%s (%s)\n" % (user.uuid, user.username))

    def print_verify(self, qh_limits, diff_quotas):
        for holder, local in diff_quotas.iteritems():
            registered = qh_limits.pop(holder, None)
            user = get_user_by_uuid(holder)
            if registered is None:
                self.stderr.write(
                    "No quota for %s (%s) in quotaholder.\n" %
                    (holder, user.username))
            else:
                self.stdout.write("Quota differ for %s (%s):\n" %
                                  (holder, user.username))
                self.stdout.write("Quota according to quotaholder:\n")
                self.stdout.write("%s\n" % (registered))
                self.stdout.write("Quota according to astakos:\n")
                self.stdout.write("%s\n\n" % (local))

        diffs = len(diff_quotas)
        if diffs:
            self.stderr.write("Quota differ for %d users.\n" % (diffs))
