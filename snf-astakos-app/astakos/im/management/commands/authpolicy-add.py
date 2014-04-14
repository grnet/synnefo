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

import string

from optparse import make_option

from snf_django.management.commands import SynnefoCommand, CommandError

from astakos.im.models import AuthProviderPolicyProfile as Profile

option_list = list(SynnefoCommand.option_list) + [
    make_option('--update',
                action='store_true',
                dest='update',
                default=False,
                help="Update an existing profile."),
    make_option('--exclusive',
                action='store_true',
                dest='exclusive',
                default=False,
                help="Apply policies to all authentication providers "
                     "except the one provided."),
]

POLICIES = ['add', 'remove', 'create', 'login', 'limit', 'required',
            'automoderate']

for p in POLICIES:
    option_list.append(make_option('--unset-%s-policy' % p,
                                   action='store_true',
                                   dest='unset_policy_%s' % p,
                                   help="Unset %s policy (only when --update)"
                                   % p.title()))
    option_list.append(make_option('--%s-policy' % p,
                                   action='store',
                                   dest='policy_%s' % p,
                                   help="%s policy" % p.title()))


class Command(SynnefoCommand):
    args = "<name> <provider_name>"
    help = "Create a new authentication provider policy profile"
    option_list = option_list

    def handle(self, *args, **options):
        if len(args) < 2:
            raise CommandError("Invalid number of arguments")

        profile = None
        update = options.get('update')
        name = args[0].strip()
        provider = args[1].strip()

        if Profile.objects.filter(name=name).count():
            if update:
                profile = Profile.objects.get(name=name)
            else:
                raise CommandError("Profile with the same name already exists")

        if not profile:
            profile = Profile()

        profile.name = name
        profile.provider = provider
        profile.is_exclusive = options.get('exclusive')

        for policy, value in options.iteritems():
            if policy.startswith('policy_') and value is not None:
                if isinstance(value, basestring) and value[0] in string.digits:
                    value = int(value)
                if value == 'False' or value == '0':
                    value = False
                if value == 'True' or value == '1':
                    value = True
                setattr(profile, policy, value)

            if update and policy.startswith('unset_'):
                policy = policy.replace('unset_', '')
                setattr(profile, policy, None)

        profile.save()
        if update:
            self.stderr.write("Profile updated\n")
        else:
            self.stderr.write("Profile stored\n")
