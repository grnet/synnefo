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

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from astakos.im.models import AstakosUser
from astakos.im.functions import (activate, deactivate)
from astakos.im import quotas
from ._common import remove_user_permission, add_user_permission, is_uuid
from snf_django.lib.db.transaction import commit_on_success_strict
import string


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
        make_option('--set-base-quota',
                    dest='set_base_quota',
                    metavar='<resource> <capacity>',
                    nargs=2,
                    help=("Set base quota for a specified resource. "
                          "The special value 'default' sets the user base "
                          "quota to the default value.")
                    ),

    )

    @commit_on_success_strict()
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a user ID")

        if args[0].isdigit():
            try:
                user = AstakosUser.objects.get(id=int(args[0]))
            except AstakosUser.DoesNotExist:
                raise CommandError("Invalid user ID")
        elif is_uuid(args[0]):
            try:
                user = AstakosUser.objects.get(uuid=args[0])
            except AstakosUser.DoesNotExist:
                raise CommandError("Invalid user UUID")
        else:
            raise CommandError(("Invalid user identification: "
                                "you should provide a valid user ID "
                                "or a valid user UUID"))

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

        set_base_quota = options.get('set_base_quota')
        if set_base_quota is not None:
            resource, capacity = set_base_quota
            self.set_limit(user, resource, capacity, False)

    def set_limit(self, user, resource, capacity, force):
        if capacity != 'default':
            try:
                capacity = int(capacity)
            except ValueError:
                m = "Please specify capacity as a decimal integer or 'default'"
                raise CommandError(m)

        try:
            quota, default_capacity = user.get_resource_policy(resource)
        except Resource.DoesNotExist:
            raise CommandError("No such resource: %s" % resource)

        current = quota.capacity if quota is not None else 'default'

        if not force:
            self.stdout.write("user: %s (%s)\n" % (user.uuid, user.username))
            self.stdout.write("default capacity: %s\n" % default_capacity)
            self.stdout.write("current capacity: %s\n" % current)
            self.stdout.write("new capacity: %s\n" % capacity)
            self.stdout.write("Confirm? (y/n) ")
            response = raw_input()
            if string.lower(response) not in ['y', 'yes']:
                self.stdout.write("Aborted.\n")
                return

        if capacity == 'default':
            try:
                quotas.remove_base_quota(user, resource)
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise CommandError("Failed to remove policy: %s" % e)
        else:
            try:
                quotas.add_base_quota(user, resource, capacity)
            except Exception as e:
                raise CommandError("Failed to add policy: %s" % e)
