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

import socket

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from astakos.im.models import AstakosUser
from astakos.im.api.callpoint import AstakosCallpoint

def filter_custom_options(options):
    base_dests = list(
        getattr(o, 'dest', None) for o in BaseCommand.option_list)
    return dict((k, v) for k, v in options.iteritems() if k not in base_dests)


class Command(BaseCommand):
    args = "<email>"
    help = "Create a user"

    option_list = BaseCommand.option_list + (
        make_option('--first-name',
                    dest='first_name',
                    metavar='NAME',
                    help="Set user's first name"),
        make_option('--last-name',
                    dest='last_name',
                    metavar='NAME',
                    help="Set user's last name"),
        make_option('--affiliation',
                    dest='affiliation',
                    metavar='AFFILIATION',
                    help="Set user's affiliation"),
        make_option('--password',
                    dest='password',
                    metavar='PASSWORD',
                    help="Set user's password"),
        make_option('--active',
                    action='store_true',
                    dest='is_active',
                    default=False,
                    help="Activate user"),
        make_option('--admin',
                    action='store_true',
                    dest='is_superuser',
                    default=False,
                    help="Give user admin rights"),
        make_option('-g',
                    action='append',
                    dest='groups',
                    help="Add user group (may be used multiple times)"),
        make_option('-p',
                    action='append',
                    dest='permissions',
                    help="Add user permission (may be used multiple times)")
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Invalid number of arguments")

        email = args[0].decode('utf8')

        try:
            validate_email(email)
        except ValidationError:
            raise CommandError("Invalid email")

        u = {'email': email}
        u.update(filter_custom_options(options))
        if not u.get('password'):
            u['password'] = AstakosUser.objects.make_random_password()

        try:
            c = AstakosCallpoint()
            r = c.create_users((u,))
        except socket.error, e:
            raise CommandError(e)
        except ValidationError, e:
            raise CommandError(e)
        else:
            failed = (res for res in r if not res.is_success)
            for r in failed:
                if not r.is_success:
                    raise CommandError(r.reason)
            if not failed:
                self.stdout.write('User created successfully')
                if not u.get('password'):
                    self.stdout.write('with password: %s' % u['password'])
