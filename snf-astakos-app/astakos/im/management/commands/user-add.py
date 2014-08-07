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

        email, first_name, last_name = args[:3]

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
