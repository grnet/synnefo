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
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from astakos.im.models import AstakosUser
from ._common import add_group_permission

class Command(BaseCommand):
    args = "<groupname> <permission> [<permissions> ...]"
    help = "Add group permissions"
    
    def handle(self, *args, **options):
        if len(args) < 2:
            raise CommandError("Please provide a group name and at least one permission")
        
        group = None
        try:
            if args[0].isdigit():
                group = Group.objects.get(id=args[0])
            else:
                group = Group.objects.get(name=args[0])
        except Group.DoesNotExist, e:
            raise CommandError("Invalid group")
        
        try:
            content_type = ContentType.objects.get(app_label='im',
                                                       model='astakosuser')
            for pname in args[1:]:
                r, created = add_group_permission(group, pname)
                if created:
                    self.stdout.write('Permission: %s created successfully\n' % pname)
                if r == 0:
                    self.stdout.write('Group has already permission: %s\n' % pname)
                else:
                    self.stdout.write('Permission: %s added successfully\n' % pname)
        except Exception, e:
            raise CommandError(e)