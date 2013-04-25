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

from astakos.im.models import AstakosUser
from synnefo.webproject.management.commands import ListCommand


def get_providers(user):
    return ','.join(
        [unicode(auth) for auth in user.auth_providers.filter(active=True)]
    )


def get_groups(user):
    return ','.join(user.groups.all().values_list('name', flat=True))


class Command(ListCommand):
    help = "List users"

    object_class = AstakosUser

    FIELDS = {
        'id': ('id', ('The id of the user')),
        'real name': ('realname', 'The name of the user'),
        'active': ('is_active', 'Whether the user is active or not'),
        'verified':
        ('email_verified', 'Whether the user has a verified email address'),
        'moderated':
        ('moderated', 'Account moderated'),
        'admin': ('is_superuser', 'Whether the user is admin or not'),
        'uuid': ('uuid', 'The uuid of the user'),
        'providers': (get_providers,
                      'The authentication providers of the user'),
        'activation_sent': ('activation_sent',
                            'The date activation sent to the user'),
        'displayname': ('username', 'The display name of the user'),
        'groups': (get_groups, 'The groups of the user')
    }

    fields = ['id', 'real name', 'active', 'verified', 'moderated', 'admin',
              'uuid']

    option_list = ListCommand.option_list + (
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
        make_option('--active',
                    action='store_true',
                    dest='active',
                    default=False,
                    help="Display only active users"),
        make_option('--pending-moderation',
                    action='store_true',
                    dest='pending_moderation',
                    default=False,
                    help="Display unmoderated users"),
        make_option('--pending-verification',
                    action='store_true',
                    dest='pending_verification',
                    default=False,
                    help="Display unverified users"),
        make_option("--displayname",
                    dest="displayname",
                    action="store_true",
                    default=False,
                    help="Display user displayname")
    )

    def handle_args(self, *args, **options):
        if options['pending']:
            self.filters['is_active'] = False

        if options['pending_send_mail']:
            self.filters['is_active'] = False
            self.filters['activation_sent'] = None

        if options['active']:
            self.filters['is_active'] = True

        if options['pending_moderation']:
            self.filters['email_verified'] = True
            self.filters['moderated'] = False

        if options['pending_verification']:
            self.filters['email_verified'] = False

        if options['auth_providers']:
            self.fields.extend(['providers'])

        if options['displayname']:
            self.fields.extend(['displayname'])
