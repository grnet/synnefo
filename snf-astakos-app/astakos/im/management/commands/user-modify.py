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

import string
from datetime import datetime

from optparse import make_option

from django.core import management
from django.db import transaction
from snf_django.management.commands import SynnefoCommand, CommandError
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from astakos.im.models import AstakosUser
from astakos.im import activation_backends
from ._common import (remove_user_permission, add_user_permission, is_uuid)

activation_backend = activation_backends.get_backend()


class Command(SynnefoCommand):
    args = "<user ID> (or --all)"
    help = "Modify a user's attributes"

    option_list = SynnefoCommand.option_list + (
        make_option('--all',
                    action='store_true',
                    default=False,
                    help=("Operate on all users. Currently only setting "
                          "base quota is supported in this mode. Can be "
                          "combined with `--exclude'.")),
        make_option('--exclude',
                    help=("If `--all' is given, exclude users given as a "
                          "list of uuids: uuid1,uuid2,uuid3")),
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
        make_option('--inactive-reason',
                    dest='inactive_reason',
                    help="Reason user got inactive"),
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
        make_option('--accept',
                    dest='accept',
                    action='store_true',
                    help="Accept user"),
        make_option('--verify',
                    dest='verify',
                    action='store_true',
                    help="Verify user email"),
        make_option('--reject',
                    dest='reject',
                    action='store_true',
                    help="Reject user"),
        make_option('--reject-reason',
                    dest='reject_reason',
                    help="Reason user got rejected"),
        make_option('--sign-terms',
                    default=False,
                    action='store_true',
                    help="Sign terms"),
        make_option('-f', '--no-confirm',
                    action='store_true',
                    default=False,
                    dest='force',
                    help="Do not ask for confirmation"),
        make_option('--set-email',
                    dest='set-email',
                    help="Change user's email"),
        make_option('--delete',
                    dest='delete',
                    action='store_true',
                    help="Delete a non-accepted user"),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if options['all']:
            if not args:
                return self.handle_all_users(*args, **options)
            else:
                raise CommandError("Please provide a user ID or --all")

        if len(args) != 1:
            raise CommandError("Please provide a user ID or --all")

        if options["exclude"] is not None:
            m = "Option --exclude is meaningful only combined with --all."
            raise CommandError(m)

        if args[0].isdigit():
            try:
                user = AstakosUser.objects.select_for_update().\
                    get(id=int(args[0]))
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

        if options.get('reject'):
            reject_reason = options.get('reject_reason', None)
            res = activation_backend.handle_moderation(
                user,
                accept=False,
                reject_reason=reject_reason)
            activation_backend.send_result_notifications(res, user)
            if res.is_error():
                self.stderr.write("Failed to reject: %s\n" % res.message)
            else:
                self.stderr.write("Account rejected\n")

        if options.get('verify'):
            res = activation_backend.handle_verification(
                user,
                user.verification_code)
            #activation_backend.send_result_notifications(res, user)
            if res.is_error():
                self.stderr.write("Failed to verify: %s\n" % res.message)
            else:
                self.stderr.write("Account verified (%s)\n"
                                  % res.status_display())

        if options.get('accept'):
            res = activation_backend.handle_moderation(user, accept=True)
            activation_backend.send_result_notifications(res, user)
            if res.is_error():
                self.stderr.write("Failed to accept: %s\n" % res.message)
            else:
                self.stderr.write("Account accepted and activated\n")

        if options.get('active'):
            res = activation_backend.activate_user(user)
            if res.is_error():
                self.stderr.write("Failed to activate: %s\n" % res.message)
            else:
                self.stderr.write("Account %s activated\n" % user.username)

        elif options.get('inactive'):
            res = activation_backend.deactivate_user(
                user,
                reason=options.get('inactive_reason', None))
            if res.is_error():
                self.stderr.write("Failed to deactivate: %s\n" % res.message)
            else:
                self.stderr.write("Account %s deactivated\n" % user.username)

        invitations = options.get('invitations')
        if invitations is not None:
            user.invitations = int(invitations)

        groupname = options.get('add-group')
        if groupname is not None:
            try:
                group = Group.objects.get(name=groupname)
                user.groups.add(group)
            except Group.DoesNotExist, e:
                self.stderr.write(
                    "Group named %s does not exist\n" % groupname)

        groupname = options.get('delete-group')
        if groupname is not None:
            try:
                group = Group.objects.get(name=groupname)
                user.groups.remove(group)
            except Group.DoesNotExist, e:
                self.stderr.write(
                    "Group named %s does not exist\n" % groupname)

        pname = options.get('add-permission')
        if pname is not None:
            try:
                r, created = add_user_permission(user, pname)
                if created:
                    self.stderr.write(
                        'Permission: %s created successfully\n' % pname)
                if r > 0:
                    self.stderr.write(
                        'Permission: %s added successfully\n' % pname)
                elif r == 0:
                    self.stderr.write(
                        'User has already permission: %s\n' % pname)
            except Exception, e:
                raise CommandError(e)

        pname = options.get('delete-permission')
        if pname is not None and not user.has_perm(pname):
            try:
                r = remove_user_permission(user, pname)
                if r < 0:
                    self.stderr.write(
                        'Invalid permission codename: %s\n' % pname)
                elif r == 0:
                    self.stderr.write('User has not permission: %s\n' % pname)
                elif r > 0:
                    self.stderr.write(
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

        if options['sign_terms']:
            user.has_signed_terms = True
            user.date_signed_terms = datetime.now()

        try:
            user.save()
        except ValidationError, e:
            raise CommandError(e)

        if password:
            self.stdout.write('User\'s new password: %s\n' % password)

        force = options['force']
        delete = options.get('delete')
        if delete:
            if user.is_accepted():
                m = "Cannot delete. User %s is accepted." % user
                raise CommandError(m)
            management.call_command('user-show', str(user.pk),
                                    list_quotas=True)

            if not force:
                self.stdout.write("About to delete user %s. " % user.uuid)
                self.confirm()
            user.delete()

        # Change users email address
        newemail = options.get('set-email', None)
        if newemail is not None:
            newemail = newemail.strip()
            try:
                validate_email(newemail)
            except ValidationError:
                m = "Invalid email address."
                raise CommandError(m)

            if AstakosUser.objects.user_exists(newemail):
                m = "A user with this email address already exists."
                raise CommandError(m)

            user.set_email(newemail)
            user.save()

    def confirm(self):
        self.stdout.write("Confirm? [y/N] ")
        try:
            response = raw_input()
        except EOFError:
            response = "ABORT"
        if string.lower(response) not in ['y', 'yes']:
            self.stderr.write("Aborted.\n")
            exit()

    def handle_all_users(self, *args, **options):
        pass
