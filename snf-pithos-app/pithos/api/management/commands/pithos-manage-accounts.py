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

from optparse import make_option

from django.core.management.base import NoArgsCommand, CommandError

from pithos.api.swiss_army import SwissArmy


class Command(NoArgsCommand):
    help = "Quotas migration helper"

    option_list = NoArgsCommand.option_list + (
        make_option('--duplicate',
                    dest='duplicate-accounts',
                    action="store_true",
                    default=True,
                    help="Display case insensitive duplicate accounts."),
        make_option('--existing',
                    dest='existing-accounts',
                    action="store_true",
                    default=False,
                    help="Display existing accounts."),
        make_option('--merge-accounts',
                    dest='merge_accounts',
                    action='store_true',
                    default=False,
                    help="Merge SOURCE_ACCOUNT and DEST_ACCOUNT."),
        make_option('--delete-account',
                    dest='delete_account',
                    action='store',
                    help="Account to be deleted."),
        make_option('--src-account',
                    dest='src_account',
                    action='store',
                    help="Account to be merged and then deleted."),
        make_option('--dest-account',
                    dest='dest_account',
                    action='store',
                    help="Account where SOURCE_ACCOUNT contents will move."),
        make_option('--dry',
                    dest='dry',
                    action="store_true",
                    default=False,
                    help="Do not commit database changes.")
    )

    def handle(self, *args, **options):
        try:
            utils = SwissArmy()
            self.strict = options.get('strict')
            self.dry = options.get('dry')

            if options.get('duplicate-accounts') and \
                    not options.get('existing-accounts') and \
                    not options.get('merge_accounts') and \
                    not options.get('delete_account'):
                duplicates = utils.duplicate_accounts()
                if duplicates:
                    msg = "The following case insensitive duplicates found: %r"
                    raise CommandError(msg % duplicates)
                else:
                    print "No duplicate accounts are found."

            if options.get('existing-accounts') and \
                    not options.get('merge_accounts') and \
                    not options.get('delete_account'):
                accounts = utils.existing_accounts()
                print "The following accounts found:"
                print "%s" % '\n'.join(accounts)

            if options.get('merge_accounts'):
                src_account = options.get('src_account')
                dest_account = options.get('dest_account')
                if not src_account:
                    raise CommandError('Please specify a source account')
                if not dest_account:
                    raise CommandError('Please specify a destination account')
                utils.merge_account(src_account, dest_account,
                                         only_stats=True)

                confirm = raw_input("Type 'yes' if you are sure you want"
                                    " to remove those entries: ")
                if not confirm == 'yes':
                    return
                else:
                    utils.merge_account(options.get('src_account'),
                                        options.get('dest_account'),
                                        only_stats=False,
                                        dry=self.dry)
                return

            if options.get('delete_account'):
                utils.delete_account(options.get('delete_account'),
                                     only_stats=True)

                confirm = raw_input("Type 'yes' if you are sure you want"
                                    " to remove those entries: ")
                if not confirm == 'yes':
                    return
                else:
                    utils.delete_account(options.get('delete_account'),
                                         only_stats=False,
                                         dry=self.dry)
                return
        except Exception, e:
            raise CommandError(e)
        finally:
            utils.backend.close()
