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

from astakos.im.models import AuthProviderPolicyProfile
from snf_django.management.commands import ListCommand


def get_groups(profile):
    return ','.join(profile.groups.values_list('name', flat=True))


def get_users(profile):
    return ','.join(profile.users.values_list('email', flat=True))


class Command(ListCommand):
    help = "List existing authentication provider policy profiles"

    object_class = AuthProviderPolicyProfile

    FIELDS = {
        'id': ('pk', 'The id of the profile'),
        'name': ('name', 'The name of the profile'),
        'provider': ('provider', 'The provider of the profile'),
        'exclusive': ('is_exclusive', 'Whether the profile is exclusive'),
        'groups': (get_groups, 'The groups of the profile'),
        'users': (get_users, 'The users of the profile'),
    }

    fields = ['id', 'name', 'provider', 'exclusive', 'groups', 'users']
