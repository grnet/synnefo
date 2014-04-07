# Copyright 2012-2014 GRNET S.A. All rights reserved.
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
from snf_django.management.commands import SynnefoCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from astakos.im.models import AstakosUser, get_latest_terms
from astakos.im.auth import make_local_user


class Command(SynnefoCommand):
    args = "<email> <first name> <last name>"
    help = "Create a user"

    option_list = SynnefoCommand.option_list + (
        make_option('--password',
                    dest='password',
                    metavar='PASSWORD',
                    help="Set user's password"),
        make_option('--admin',
                    action='store_true',
                    dest='is_superuser',
                    default=False,
                    help="Give user admin rights"),
        make_option('-g',
                    action='append',
                    dest='groups',
                    default=[],
                    help="Add user group (may be used multiple times)"),
        make_option('-p',
                    action='append',
                    dest='permissions',
                    default=[],
                    help="Add user permission (may be used multiple times)")
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if len(args) != 3:
            raise CommandError("Invalid number of arguments")

        email, first_name, last_name = map(lambda arg: arg.decode('utf8'),
                                           args[:3])

        password = options['password'] or \
            AstakosUser.objects.make_random_password()

        try:
            validate_email(email)
        except ValidationError:
            raise CommandError("Invalid email")

        has_signed_terms = not(get_latest_terms())

        try:
            user = make_local_user(
                email, first_name=first_name, last_name=last_name,
                password=password, has_signed_terms=has_signed_terms)
            if options['is_superuser']:
                user.is_superuser = True
                user.save()

        except BaseException, e:
            raise CommandError(e)
        else:
            self.stdout.write('User created successfully with UUID: %s'
                              % user.uuid)
            if not options.get('password'):
                self.stdout.write(' and password: %s\n' % password)
            else:
                self.stdout.write('\n')

            try:
                map(user.add_permission, options['permissions'])
                map(user.add_group, options['groups'])
            except BaseException, e:
                raise CommandError(e)
