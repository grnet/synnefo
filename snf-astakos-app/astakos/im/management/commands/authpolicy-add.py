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

import string

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from astakos.im.models import AuthProviderPolicyProfile as Profile

option_list = list(BaseCommand.option_list) + [
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


class Command(BaseCommand):
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
            print "Profile updated"
        else:
            print "Profile stored"
