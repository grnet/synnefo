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
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from astakos.im.models import AstakosUser
from astakos.im.functions import activate, deactivate
from ._common import remove_user_permission, add_user_permission


class Command(BaseCommand):
    args = "<user ID>"
    help = "Modify a user's attributes"

    option_list = BaseCommand.option_list + (
        make_option('--invitations',
                    dest='invitations',
                    metavar='NUM',
                    help="Update user's invitations"),
        make_option('--level',
                    dest='level',
                    metavar='NUM',
                    help="Update user's level"),
        make_option('--password',
                    dest='password',
                    metavar='PASSWORD',
                    help="Set user's password"),
        make_option('--renew-token',
                    action='store_true',
                    dest='renew_token',
                    default=False,
                    help="Renew the user's token"),
        make_option('--renew-password',
                    action='store_true',
                    dest='renew_password',
                    default=False,
                    help="Renew the user's password"),
        make_option('--set-admin',
                    action='store_true',
                    dest='admin',
                    default=False,
                    help="Give user admin rights"),
        make_option('--set-noadmin',
                    action='store_true',
                    dest='noadmin',
                    default=False,
                    help="Revoke user's admin rights"),
        make_option('--set-active',
                    action='store_true',
                    dest='active',
                    default=False,
                    help="Change user's state to active"),
        make_option('--set-inactive',
                    action='store_true',
                    dest='inactive',
                    default=False,
                    help="Change user's state to inactive"),
        make_option('--add-group',
                    dest='add-group',
                    help="Add user group"),
        make_option('--delete-group',
                    dest='delete-group',
                    help="Delete user group"),
        make_option('--add-permission',
                    dest='add-permission',
                    help="Add user permission"),
        make_option('--delete-permission',
                    dest='delete-permission',
                    help="Delete user permission"),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a user ID")

        if args[0].isdigit():
            user = AstakosUser.objects.get(id=int(args[0]))
        else:
            raise CommandError("Invalid ID")

        if not user:
            raise CommandError("Unknown user")

        if options.get('admin'):
            user.is_superuser = True
        elif options.get('noadmin'):
            user.is_superuser = False

        if options.get('active'):
            activate(user)
        elif options.get('inactive'):
            deactivate(user)

        invitations = options.get('invitations')
        if invitations is not None:
            user.invitations = int(invitations)

        groupname = options.get('add-group')
        if groupname is not None:
            try:
                group = Group.objects.get(name=groupname)
                user.groups.add(group)
            except Group.DoesNotExist, e:
                self.stdout.write(
                    "Group named %s does not exist\n" % groupname)

        groupname = options.get('delete-group')
        if groupname is not None:
            try:
                group = Group.objects.get(name=groupname)
                user.groups.remove(group)
            except Group.DoesNotExist, e:
                self.stdout.write(
                    "Group named %s does not exist\n" % groupname)

        pname = options.get('add-permission')
        if pname is not None:
            try:
                r, created = add_user_permission(user, pname)
                if created:
                    self.stdout.write(
                        'Permission: %s created successfully\n' % pname)
                if r > 0:
                    self.stdout.write(
                        'Permission: %s added successfully\n' % pname)
                elif r == 0:
                    self.stdout.write(
                        'User has already permission: %s\n' % pname)
            except Exception, e:
                raise CommandError(e)

        pname = options.get('delete-permission')
        if pname is not None and not user.has_perm(pname):
            try:
                r = remove_user_permission(user, pname)
                if r < 0:
                    self.stdout.write(
                        'Invalid permission codename: %s\n' % pname)
                elif r == 0:
                    self.stdout.write('User has not permission: %s\n' % pname)
                elif r > 0:
                    self.stdout.write(
                        'Permission: %s removed successfully\n' % pname)
            except Exception, e:
                raise CommandError(e)

        level = options.get('level')
        if level is not None:
            user.level = int(level)

        password = options.get('password')
        if password is not None:
            user.set_password(password)

        password = None
        if options['renew_password']:
            password = AstakosUser.objects.make_random_password()
            user.set_password(password)

        if options['renew_token']:
            user.renew_token()

        try:
            user.save()
        except ValidationError, e:
            raise CommandError(e)

        if password:
            self.stdout.write('User\'s new password: %s\n' % password)
