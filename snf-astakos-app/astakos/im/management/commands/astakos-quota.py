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
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from astakos.im.models import sync_all_users, sync_users, AstakosUser
from astakos.im.functions import get_user_by_uuid
from astakos.im.management.commands._common import is_uuid, is_email

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Inspect quotaholder status"

    option_list = BaseCommand.option_list + (
        make_option('--list',
                    action='store_true',
                    dest='list',
                    default=False,
                    help="List all quotas (default)"),
        make_option('--verify',
                    action='store_true',
                    dest='verify',
                    default=False,
                    help="Check if quotaholder is in sync with astakos"),
        make_option('--sync',
                    action='store_true',
                    dest='sync',
                    default=False,
                    help="Sync quotaholder"),
        make_option('--user',
                    metavar='<uuid or email>',
                    dest='user',
                    help="List quotas for a specified user"),
    )

    def handle(self, *args, **options):
        sync = options['sync']
        verify = options['verify'] or sync
        user_ident = options['user']

        if user_ident is not None:
            log = self.run_sync_user(user_ident, sync)
        else:
            log = self.run(sync)

        ex, nonex, qh_l, qh_c, astakos_i, astakos_q, info = log

        if verify:
            self.print_verify(nonex, qh_l, astakos_q)

        else:
            self.list_quotas(qh_l, qh_c, astakos_i, info)

    @transaction.commit_on_success
    def run_sync_user(self, user_ident, sync):
        if is_uuid(user_ident):
            try:
                user = AstakosUser.objects.get(uuid=user_ident)
            except AstakosUser.DoesNotExist:
                raise CommandError('Not found user having uuid: %s' %
                                   user_ident)
        elif is_email(user_ident):
            try:
                user = AstakosUser.objects.get(username=user_ident)
            except AstakosUser.DoesNotExist:
                raise CommandError('Not found user having email: %s' %
                                   user_ident)
        else:
            raise CommandError('Please specify user by uuid or email')

        if not user.email_verified and sync:
            raise CommandError('User %s is not verified.' % user.uuid)

        try:
            return sync_users([user], sync=sync)
        except BaseException, e:
            logger.exception(e)
            raise CommandError("Failed to compute quotas.")

    @transaction.commit_on_success
    def run(self, sync):
        try:
            self.stderr.write("Calculating all quotas...\n")
            return sync_all_users(sync=sync)
        except BaseException, e:
            logger.exception(e)
            raise CommandError("Syncing failed.")

    def list_quotas(self, qh_limits, qh_counters, astakos_initial, info):
        labels = ('uuid', 'email', 'resource', 'initial', 'total', 'usage')
        columns = (36, 30, 24, 12, 12, 12)

        line = ' '.join(l.rjust(w) for l, w in zip(labels, columns))
        self.stdout.write(line + '\n')
        sep = '-' * len(line)
        self.stdout.write(sep + '\n')

        for holder, resources in qh_limits.iteritems():
            h_counters = qh_counters[holder]
            h_initial = astakos_initial[holder]
            email = info[holder]
            for resource, limits in resources.iteritems():
                initials = h_initial[resource]
                initial = str(initials.capacity)
                capacity = str(limits.capacity)
                c = h_counters[resource]
                used = str(c.imported - c.exported + c.returned - c.released)

                fields = holder, email, resource, initial, capacity, used
                output = []
                for field, width in zip(fields, columns):
                    s = field.rjust(width)
                    output.append(s)

                line = ' '.join(output)
                self.stdout.write(line + '\n')

    def print_verify(self,
                     nonexisting,
                     qh_limits,
                     astakos_quotas):

            if nonexisting:
                self.stdout.write("Users not registered in quotaholder:\n")
                for user in nonexisting:
                    self.stdout.write("%s\n" % (user))
                self.stdout.write("\n")

            diffs = 0
            for holder, local in astakos_quotas.iteritems():
                registered = qh_limits.pop(holder, None)
                if registered is None:
                    diffs += 1
                    self.stdout.write("No quotas for %s in quotaholder.\n\n" %
                                      (get_user_by_uuid(holder)))
                elif local != registered:
                    diffs += 1
                    self.stdout.write("Quotas differ for %s:\n" %
                                      (get_user_by_uuid(holder)))
                    self.stdout.write("Quotas according to quotaholder:\n")
                    self.stdout.write("%s\n" % (registered))
                    self.stdout.write("Quotas according to astakos:\n")
                    self.stdout.write("%s\n\n" % (local))

            if diffs:
                self.stdout.write("Quotas differ for %d users.\n" % (diffs))
