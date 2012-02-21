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

from astakos.im.models import AstakosUser
    

class Command(BaseCommand):
    args = "<user_id or email> [user_id or email] ..."
    help = "Activates one or more users"
    
    def handle(self, *args, **options):
        if not args:
            raise CommandError("No user was given")
        
        for email_or_id in args:
            try:
                if email_or_id.isdigit():
                    user = AstakosUser.objects.get(id=int(email_or_id))
                else:
                    user = AstakosUser.objects.get(email=email_or_id)
            except AstakosUser.DoesNotExist:
                field = 'id' if email_or_id.isdigit() else 'email'
                msg = "Unknown user with %s '%s'" % (field, email_or_id)
                self.stderr.write(msg + '\n')
                continue
            
            if user.is_active:
                msg = "User '%s' already active\n" % (user.email,)
                self.stderr.write(msg)
                continue
            
            user.is_active = True
            user.save()
            
            self.stdout.write("Activated '%s'\n" % (user.email,))
