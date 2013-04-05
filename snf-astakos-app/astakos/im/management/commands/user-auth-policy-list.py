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

from astakos.im.models import AuthProviderPolicyProfile
from synnefo.webproject.management.commands import ListCommand


class Command(ListCommand):
    help = "List existing authentication provider policy profiles"

    object_class = AuthProviderPolicyProfile

    def get_groups(profile):
        return ','.join(profile.groups.values_list('name', flat=True))

    def get_users(profile):
        return ','.join(profile.users.values_list('email', flat=True))

    FIELDS = {
        'id': ('pk', 'The id of the profile'),
        'name': ('name', 'The name of the profile'),
        'provider': ('provider', 'The provider of the profile'),
        'exclusive': ('is_exclusive', 'Whether the profile is exclusive or not'),
        'groups': (get_groups, 'The groups of the profile'),
        'users': (get_users, 'The users of the profile'),
    }

    fields = ['id', 'name', 'provider', 'exclusive', 'groups', 'users']
