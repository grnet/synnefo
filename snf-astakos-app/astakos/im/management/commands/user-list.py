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

from optparse import make_option

from astakos.im.models import AstakosUser
from snf_django.management.commands import ListCommand


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
        'realname': ('realname', 'The name of the user'),
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
        'groups': (get_groups, 'The groups of the user'),
        'last_login_details': ('last_login_info_display',
                             'User last login dates for each login method'),
        'last_login': ('last_login', 'User last login date')
    }

    fields = ['id', 'displayname', 'realname', 'uuid', 'active', 'admin']

    option_list = ListCommand.option_list + (
        make_option('--auth-providers',
                    action='store_true',
                    dest='auth_providers',
                    default=False,
                    help="Display user authentication providers"),
        make_option('--group',
                    action='append',
                    dest='groups',
                    default=None,
                    metavar="GROUP",
                    help="Only show users that belong to the specified"
                         " group. Can be used multiple times."),
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
        make_option("--display-mails",
                    dest="displayname",
                    action="store_true",
                    default=False,
                    help="Display user email (enabled by default)")
    )

    def handle_args(self, *args, **options):
        if options['active']:
            self.filters['is_active'] = True

        if options['pending_moderation']:
            self.filters['email_verified'] = True
            self.filters['moderated'] = False

        if options['pending_verification']:
            self.filters['email_verified'] = False

        if options['groups']:
            self.filters['groups__name__in'] = options['groups']

        if options['auth_providers']:
            self.fields.extend(['providers'])

        DISPLAYNAME = 'displayname'
        if options[DISPLAYNAME] and DISPLAYNAME not in self.fields:
            self.fields.extend([DISPLAYNAME])
