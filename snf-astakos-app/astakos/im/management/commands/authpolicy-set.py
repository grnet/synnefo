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

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError

from astakos.im.models import AuthProviderPolicyProfile as Profile
from astakos.im.models import AstakosUser, Group

option_list = BaseCommand.option_list + (
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


class Command(BaseCommand):
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
