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

from django.core.management.base import NoArgsCommand

from astakos.im.models import AstakosUser, AstakosUserAuthProvider, Group

from ._common import format, filter_results


class Command(NoArgsCommand):
    help = "List users"

    FIELDS = AstakosUser._meta.get_all_field_names()

    option_list = NoArgsCommand.option_list + (
        make_option('-c',
                    action='store_true',
                    dest='csv',
                    default=False,
                    help="Use pipes to separate values"),
        make_option('-p',
                    action='store_true',
                    dest='pending',
                    default=False,
                    help="List only users pending activation"),
        make_option('--auth-providers',
                    action='store_true',
                    dest='auth_providers',
                    default=False,
                    help="Display user authentication providers"),
        make_option('--group',
                    action='append',
                    dest='groups',
                    default=None,
                    help="Only show users that belong to the specified goups"),
        make_option('-n',
                    action='store_true',
                    dest='pending_send_mail',
                    default=False,
                    help="List only users who have not received activation"),
        make_option('--uuid',
                    action='store_true',
                    dest='only_uuid',
                    default=False,
                    help="Only display user uuid (default)"),
        make_option('--displayname',
                    action='store_true',
                    dest='displayname',
                    default=False,
                    help="Display both uuid and display name"),
        make_option('--active',
                    action='store_true',
                    dest='active',
                    default=False,
                    help="Display only active users"),
        make_option('--filter-by',
                    dest='filter_by',
                    help="Filter results. Comma seperated list of key `cond`"
                    " val pairs that displayed entries must satisfy. e.g."
                    " --filter-by \"is_active=True,email_verified=True\"."
                    " Available keys are: %s" % ", ".join(FIELDS)),

    )

    def handle_noargs(self, **options):
        users = AstakosUser.objects.all().order_by('id')
        if options['pending']:
            users = users.filter(is_active=False)
        elif options['pending_send_mail']:
            users = users.filter(is_active=False, activation_sent=None)

        active_only = options['active']
        if active_only:
            users = filter_results(users, "is_active=True")

        filter_by = options['filter_by']
        if filter_by:
            users = filter_results(users, filter_by)

        displayname = options['displayname']

        ids = [user.id for user in users]
        auths = AstakosUserAuthProvider.objects.filter(
            user__in=ids, active=True)

        all_auth = partition_by(lambda a: a.user_id, auths)

        labels = filter(lambda x: x is not Omit,
                        [('id', 3),
                         ('display name', 24) if displayname else Omit,
                         ('real name', 24),
                         ('active', 6),
                         ('admin', 5),
                         ('uuid', 36),
                         ('providers', 24),
                         ])

        columns = [c for (l, c) in labels]

        if not options['csv']:
            line = ' '.join(l.rjust(w) for l, w in labels)
            self.stdout.write(line + '\n')
            sep = '-' * len(line)
            self.stdout.write(sep + '\n')

        for user in users:
            id = str(user.id)
            active = user.is_active
            admin = user.is_superuser
            uuid = user.uuid or ''
            auths = all_auth[user.id]
            auth_display = ",".join(unicode(auth) for auth in auths)

            elems = filter(lambda x: x is not Omit,
                           [id,
                            user.username if displayname else Omit,
                            user.realname,
                            active, admin, uuid,
                            auth_display,
                            ])
            fields = (format(elem) for elem in elems)

            if options['csv']:
                line = '|'.join(fields)
            else:
                line = ' '.join(f.rjust(w) for f, w in zip(fields, columns))

            self.stdout.write(line + '\n')


class Omit(object):
    pass


def partition_by(f, l):
    d = {}
    for x in l:
        group = f(x)
        group_l = d.get(group, [])
        group_l.append(x)
        d[group] = group_l
    return d
