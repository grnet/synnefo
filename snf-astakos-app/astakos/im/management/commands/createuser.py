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
from random import choice
from string import digits, lowercase, uppercase
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group

from astakos.im.models import AstakosUser
from astakos.im.util import reserved_email

from ._common import add_user_permission

class Command(BaseCommand):
    args = "<email> <first name> <last name> <affiliation>"
    help = "Create a user"
    
    option_list = BaseCommand.option_list + (
        make_option('--active',
            action='store_true',
            dest='active',
            default=False,
            help="Activate user"),
        make_option('--admin',
            action='store_true',
            dest='admin',
            default=False,
            help="Give user admin rights"),
        make_option('--password',
            dest='password',
            metavar='PASSWORD',
            help="Set user's password"),
        make_option('--add-group',
            dest='add-group',
            help="Add user group"),
        make_option('--add-permission',
            dest='add-permission',
            help="Add user permission")
        )
    
    def handle(self, *args, **options):
        if len(args) != 4:
            raise CommandError("Invalid number of arguments")
        
        args = [a.decode('utf8') for a in args]
        email, first, last, affiliation = args
        
        try:
            validate_email( email )
        except ValidationError:
            raise CommandError("Invalid email")
        
        username =  uuid4().hex[:30]
        password = options.get('password')
        if password is None:
            password = AstakosUser.objects.make_random_password()
        
        if reserved_email(email):
            raise CommandError("A user with this email already exists")
        
        user = AstakosUser(username=username, first_name=first, last_name=last,
                           email=email, affiliation=affiliation,
                           provider='local')
        user.set_password(password)
        user.renew_token()
        
        if options['active']:
            user.is_active = True
        if options['admin']:
            user.is_admin = True
        
        try:
            user.save()
        except socket.error, e:
            raise CommandError(e)
        except ValidationError, e:
            raise CommandError(e)
        else:
            msg = "Created user id %d" % (user.id,)
            if options['password'] is None:
                msg += " with password '%s'" % (password,)
            self.stdout.write(msg + '\n')
            
            groupname = options.get('add-group')
            if groupname is not None:
                try:
                    group = Group.objects.get(name=groupname)
                    user.groups.add(group)
                    self.stdout.write('Group: %s added successfully\n' % groupname)
                except Group.DoesNotExist, e:
                    self.stdout.write('Group named %s does not exist\n' % groupname)
            
            pname = options.get('add-permission')
            if pname is not None:
                try:
                    r, created = add_user_permission(user, pname)
                    if created:
                        self.stdout.write('Permission: %s created successfully\n' % pname)
                    if r > 0:
                        self.stdout.write('Permission: %s added successfully\n' % pname)
                    elif r==0:
                        self.stdout.write('User has already permission: %s\n' % pname)
                except Exception, e:
                    raise CommandError(e)