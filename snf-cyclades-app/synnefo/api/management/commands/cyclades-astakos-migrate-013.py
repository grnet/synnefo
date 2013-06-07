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

import itertools
import warnings
import functools

from optparse import make_option

from django.core.management.base import NoArgsCommand, CommandError, BaseCommand
from django.db import transaction
from django.conf import settings

from synnefo.api.util import get_existing_users
from synnefo.lib.utils import case_unique
from synnefo.db.models import Network, VirtualMachine
from synnefo.userdata.models import PublicKeyPair

from snf_django.lib import astakos

def warn(*msgs):
    print "WARNING: %s" % ' '.join(msgs)

get_displayname = functools.partial(astakos.get_displayname,
                                 settings.CYCLADES_SERVICE_TOKEN,
                                 url=settings.ASTAKOS_URL.replace('im/authenticate',
                                                                 'service/api/user_catalogs'))
get_user_uuid = functools.partial(astakos.get_user_uuid,
                                 settings.CYCLADES_SERVICE_TOKEN,
                                 url=settings.ASTAKOS_URL.replace('im/authenticate',
                                                                 'service/api/user_catalogs'))

def _validate_db_state(usernames):

    usernames = filter(bool, usernames)
    invalid_case_users = case_unique(usernames)
    if invalid_case_users:
        invalid_case_users.append(invalid_case_users[0].lower())
        raise CommandError("Duplicate case insensitive user identifiers exist %r" % invalid_case_users)

    uuidusers = filter(lambda uid:'@' in uid or uid == None, usernames)
    if len(uuidusers) != len(usernames):
        warn('It seems that mixed uuid/email user identifiers exist in database.')
        return False

    return True


@transaction.commit_manually
def delete_user(username, only_stats=True, dry=True):
    vms = VirtualMachine.objects.filter(userid__exact=username)
    networks = Network.objects.filter(userid__exact=username)
    keys = PublicKeyPair.objects.filter(user__exact=username)

    if not len(list(itertools.ifilter(bool, map(lambda q: q.count(), [vms,
                                                                      networks,
                                                                      keys])))):
        print "No entries exist for '%s'" % username
        return -1

    if only_stats:
        print "The following entries will be deleted if you decide to remove this user"
        print "%d Virtual Machines" % vms.exclude(operstate='DESTROYED').count()
        print "%d Destroyed Virtual Machines" % vms.filter(operstate='DESTROYED').count()
        print "%d Networks" % networks.count()
        print "%d PublicKeyPairs" % keys.count()
        return

    for o in itertools.chain(vms, networks):
        o.delete()

    for key in keys:
        key.delete()

    if dry:
        print "Skipping database commit."
        transaction.rollback()
    else:
        transaction.commit()
        print "User entries removed."


@transaction.commit_on_success
def merge_user(username):
    vms = VirtualMachine.objects.filter(userid__iexact=username)
    networks = Network.objects.filter(userid__iexact=username)
    keys = PublicKeyPair.objects.filter(user__iexact=username)

    for o in itertools.chain(vms, networks):
        o.userid = username.lower()
        o.save()

    for key in keys:
        key.user = username.lower()
        key.save()


def migrate_user(username, uuid):
    """
    Warn: no transaction handling. Consider wrapping within another function.
    """
    vms = VirtualMachine.objects.filter(userid__exact=username)
    networks = Network.objects.filter(userid__exact=username)
    keys = PublicKeyPair.objects.filter(user__exact=username)

    for o in itertools.chain(vms, networks):
        o.userid = uuid or o.userid
        o.save()

    for key in keys:
        key.user = uuid
        key.save()


@transaction.commit_manually
def migrate_users(usernames, dry=True):
    usernames = filter(bool, usernames)
    count = 0
    for u in usernames:
        if not '@' in u:
            warn('Skipping %s. It doesn\'t seem to be an email' % u)
            continue

        try:
            uuid = get_user_uuid(u)
            print "%s -> %s" % (u, uuid)
            if not uuid:
                raise Exception("No uuid for %s" % u)
            migrate_user(u, uuid)
            count += 1
        except Exception, e:
            print "ERROR: User id migration failed (%s)" % e

    if dry:
        print "Skipping database commit."
        transaction.rollback()
    else:
        transaction.commit()
        print "Migrated %d users" % count


class Command(NoArgsCommand):
    help = "Quotas migration helper"

    option_list = BaseCommand.option_list + (
        make_option('--strict',
                    dest='strict',
                    action="store_false",
                    default=True,
                    help="Exit on warnings."),
        make_option('--validate-db',
                    dest='validate',
                    action="store_true",
                    default=True,
                    help=("Check if cyclades database contents are valid for "
                          "migration.")),
        make_option('--migrate-users',
                    dest='migrate_users',
                    action="store_true",
                    default=False,
                    help=("Convert emails to uuids for all users stored in "
                          "database.")),
        make_option('--merge-user',
                    dest='merge_user',
                    default=False,
                    help="Merge case insensitive duplicates of a user."),
        make_option('--delete-user',
                    dest='delete_user',
                    action='store',
                    default=False,
                    help="Delete user entries."),
        make_option('--user-entries',
                    dest='user_entries',
                    action='store',
                    default=False,
                    help="Display user summary."),
        make_option('--dry',
                    dest='dry',
                    action="store_true",
                    default=False,
                    help="Do not commit database changes. Do not communicate "
                         "with quotaholder"),
        make_option('--user',
                    dest='user',
                    action="store",
                    default=False,)
    )

    def resolve_conflicts(self, options):
        conflicting = map(options.get, ['migrate_users',
                                        'merge_user'])
        if len(filter(bool, conflicting)) > 1:
            raise CommandError('You can use only one of --validate,'
                               '--migrate-users')

    def handle(self, *args, **options):
        self.resolve_conflicts(options)
        self.strict = options.get('strict')
        self.dry = options.get('dry')

        if options.get('validate') and not options.get('merge_user') and not \
                options.get('delete_user') and not options.get('user_entries'):
            usernames = get_existing_users()
            _validate_db_state(usernames)

        if options.get('migrate_users'):
            migrate_users(usernames, dry=self.dry)

        if options.get('merge_user'):
            merge_user(options.get('merge_user'))
            print "Merge finished."

        if options.get('delete_user'):
            entries = delete_user(options.get('delete_user'), only_stats=True)
            if entries == -1:
                return

            confirm = raw_input("Type 'yes of course' if you are sure you want"
                                " to remove those entries: ")
            if not confirm == 'yes of course':
                return
            else:
                delete_user(options.get('delete_user'), only_stats=False,
                            dry=self.dry)

        if options.get('user_entries'):
            delete_user(options.get('user_entries'))
