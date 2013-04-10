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

from django.core.management.base import BaseCommand, CommandError

from astakos.im.models import AstakosUser, get_latest_terms
from astakos.im.util import model_to_dict
from synnefo.lib.ordereddict import OrderedDict

from ._common import format

import uuid


class Command(BaseCommand):
    args = "<user ID or email>"
    help = "Show user info"

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a user ID or email")

        identifier = args[0]
        if identifier.isdigit():
            users = AstakosUser.objects.filter(id=int(identifier))
        else:
            try:
                uuid.UUID(identifier)
            except:
                users = AstakosUser.objects.filter(email__iexact=identifier)
            else:
                users = AstakosUser.objects.filter(uuid=identifier)
        if users.count() == 0:
            field = 'id' if identifier.isdigit() else 'email'
            msg = "Unknown user with %s '%s'" % (field, identifier)
            raise CommandError(msg)

        for user in users:
            quotas = user.all_quotas()
            showable_quotas = {}
            for resource, limits in quotas.iteritems():
                showable_quotas[resource] = limits.capacity

            settings_dict = {}
            settings = user.settings()
            for setting in settings:
                settings_dict[setting.setting] = setting.value

            kv = OrderedDict(
                [
                    ('id', user.id),
                    ('uuid', user.uuid),
                    ('email', user.email),
                    ('first name', user.first_name),
                    ('last name', user.last_name),
                    ('active', user.is_active),
                    ('admin', user.is_superuser),
                    ('last login', user.last_login),
                    ('date joined', user.date_joined),
                    ('last update', user.updated),
                    #('token', user.auth_token),
                    ('token expiration', user.auth_token_expires),
                    ('invitations', user.invitations),
                    ('invitation level', user.level),
                    ('providers', user.auth_providers_display),
                    ('verified', user.is_verified),
                    ('has_credits', format(user.has_credits)),
                    ('groups', [elem.name for elem in user.groups.all()]),
                    ('permissions', [elem.codename
                                     for elem in user.user_permissions.all()]),
                    ('group_permissions', user.get_group_permissions()),
                    ('email_verified', user.email_verified),
                    ('username', user.username),
                    ('activation_sent_date', user.activation_sent),
                ])

            if settings_dict:
                kv['settings'] = settings_dict

            kv['resources'] = showable_quotas

            if get_latest_terms():
                has_signed_terms = user.signed_terms
                kv['has_signed_terms'] = has_signed_terms
                if has_signed_terms:
                    kv['date_signed_terms'] = user.date_signed_terms

            self.stdout.write(format(kv))
            self.stdout.write('\n')
