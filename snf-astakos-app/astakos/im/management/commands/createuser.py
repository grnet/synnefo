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
from random import choice
from string import digits, lowercase, uppercase
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from astakos.im.models import AstakosUser

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
            help="Set user's password")
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
        
        try:
            AstakosUser.objects.get(email=email)
            raise CommandError("A user with this email already exists")
        except AstakosUser.DoesNotExist:
            pass
        
        user = AstakosUser(username=username, first_name=first, last_name=last,
                           email=email, affiliation=affiliation,
                           provider='local')
        user.set_password(password)
        user.renew_token()
        
        if options['active']:
            user.is_active = True
        if options['admin']:
            user.is_admin = True
        
        user.save()
        
        msg = "Created user id %d" % (user.id,)
        if options['password'] is None:
            msg += " with password '%s'" % (password,)
        self.stdout.write(msg + '\n')
