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

from astakos.im import transaction
from snf_django.management.commands import SynnefoCommand, CommandError
from astakos.im.models import AuthProviderPolicyProfile as Profile
from astakos.im.models import AstakosUser, Group

option_list = SynnefoCommand.option_list + (
    make_option('--group',
                action='append',
                dest='groups',
                default=[],
                help="Assign profile to the provided group id. Option may "
                     "be used more than once."),
    make_option('--user',
                action='append',
                dest='users',
                default=[],
                help="Assign profile to the provided user id. Option may "
                     "be used more than once.")
)


@transaction.commit_on_success
def update_profile(profile, users, groups):
    profile.groups.all().delete()
    profile.users.all().delete()
    profile.groups.add(*groups)
    profile.users.add(*users)


class Command(SynnefoCommand):
    args = "<name> <provider_name>"
    help = "Assign an existing authentication provider policy profile to " + \
           "a user or group. All previously set "
    option_list = option_list

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("Invalid number of arguments")

        name = args[0].strip()
        try:
            profile = Profile.objects.get(name=name)
        except Profile.DoesNotExist:
            raise CommandError("Invalid profile name")

        users = []
        try:
            users = [AstakosUser.objects.get(pk=int(pk)) for pk in
                     options.get('users')]
        except AstakosUser.DoesNotExist:
            raise CommandError("Invalid user id")

        groups = []
        try:
            groups = [Group.objects.get(pk=int(pk)) for pk in
                      options.get('groups')]
        except Group.DoesNotExist:
            raise CommandError("Invalid group id")

        update_profile(profile, users, groups)
