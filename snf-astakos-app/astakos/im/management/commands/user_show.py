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

from django.core.management.base import BaseCommand, CommandError

from astakos.im.models import AstakosUser, get_latest_terms

from ._common import format_bool, format_date


class Command(BaseCommand):
    args = "<user ID or email>"
    help = "Show user info"
    
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a user ID or email")
        
        email_or_id = args[0]
        if email_or_id.isdigit():
            users = AstakosUser.objects.filter(id=int(email_or_id))
        else:
            users = AstakosUser.objects.filter(email=email_or_id)
        if users.count() == 0:
            field = 'id' if email_or_id.isdigit() else 'email'
            msg = "Unknown user with %s '%s'" % (field, email_or_id)
            raise CommandError(msg)
        
        for user in users:
            kv = {
                'id': user.id,
                'email': user.email,
                'first name': user.first_name,
                'last name': user.last_name,
                'active': format_bool(user.is_active),
                'admin': format_bool(user.is_superuser),
                'last login': format_date(user.last_login),
                'date joined': format_date(user.date_joined),
                'last update': format_date(user.updated),
                #'token': user.auth_token,
                'token expiration': format_date(user.auth_token_expires),
                'invitations': user.invitations,
                'invitation level': user.level,
                'provider': user.provider,
                'verified': format_bool(user.is_verified),
                'has_credits': format_bool(user.has_credits),
                'groups': [elem.name for elem in user.astakos_groups.all()],
                'permissions': [elem.codename for elem in user.user_permissions.all()],
                'group_permissions': user.get_group_permissions(),
                'third_party_identifier': user.third_party_identifier,
                'email_verified': format_bool(user.email_verified),
                'username': user.username,
                'activation_sent_date': format_date(user.activation_sent),
                'resources' : user.quota
            }
            if get_latest_terms():
                has_signed_terms = user.signed_terms()
                kv['has_signed_terms'] = format_bool(has_signed_terms)
                if has_signed_terms:
                    kv['date_signed_terms'] = format_date(user.date_signed_terms)
            
            for key, val in sorted(kv.items()):
                line = '%s: %s\n' % (key.rjust(22), val)
                self.stdout.write(line.encode('utf8'))
            self.stdout.write('\n')