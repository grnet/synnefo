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
from django.core.management.base import CommandError

from astakos.im.models import AstakosUser
from astakos.im.quotas import set_user_quota, list_user_quotas
from astakos.im.functions import get_user_by_uuid
from astakos.im.management.commands._common import is_uuid, is_email
from snf_django.lib.db.transaction import commit_on_success_strict
from synnefo.webproject.management.commands import SynnefoCommand
from synnefo.webproject.management import utils
from ._common import show_quotas

import logging
logger = logging.getLogger(__name__)


class Command(SynnefoCommand):
    help = "Inspect quotaholder status"

    option_list = SynnefoCommand.option_list + (
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

    @commit_on_success_strict()
    def handle(self, *args, **options):
        sync = options['sync']
        verify = options['verify']
        user_ident = options['user']
        list_only = not sync and not verify

        if user_ident is not None:
            users = [self.get_user(user_ident)]
        else:
            users = AstakosUser.objects.verified()

        try:
            qh_limits, qh_quotas, astakos_i, diff_q = list_user_quotas(users)
        except BaseException as e:
            logger.exception(e)
            raise CommandError("Failed to compute quotas.")

        info = {}
        for user in users:
            info[user.uuid] = user.email

        if list_only:
            print_data, labels = show_quotas(qh_quotas, astakos_i, info)
            utils.pprint_table(self.stdout, print_data, labels,
                               options["output_format"])

        else:
            if verify:
                self.print_verify(qh_limits, diff_q)
            if sync:
                try:
                    set_user_quota(diff_q)
                except BaseException as e:
                    logger.exception(e)
                    raise CommandError("Failed to sync quotas.")
                self.print_sync(diff_q)

    def get_user(self, user_ident):
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

        return user

    def print_sync(self, diff_quotas):
        size = len(diff_quotas)
        if size == 0:
            self.stdout.write("No sync needed.\n")
        else:
            self.stdout.write("Synced %s users:\n" % size)
            for holder in diff_quotas.keys():
                user = get_user_by_uuid(holder)
                self.stdout.write("%s (%s)\n" % (holder, user.username))

    def print_verify(self,
                     qh_limits,
                     diff_quotas):

            for holder, local in diff_quotas.iteritems():
                registered = qh_limits.pop(holder, None)
                user = get_user_by_uuid(holder)
                if registered is None:
                    self.stdout.write(
                        "No quotas for %s (%s) in quotaholder.\n" %
                        (holder, user.username))
                else:
                    self.stdout.write("Quotas differ for %s (%s):\n" %
                                      (holder, user.username))
                    self.stdout.write("Quotas according to quotaholder:\n")
                    self.stdout.write("%s\n" % (registered))
                    self.stdout.write("Quotas according to astakos:\n")
                    self.stdout.write("%s\n\n" % (local))

            diffs = len(diff_quotas)
            if diffs:
                self.stdout.write("Quotas differ for %d users.\n" % (diffs))
