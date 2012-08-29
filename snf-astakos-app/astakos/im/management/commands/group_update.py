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

from astakos.im.models import AstakosGroup
from ._common import add_group_permission, remove_group_permission

class Command(BaseCommand):
    args = "<groupname>"
    help = "Update group"
    
    option_list = BaseCommand.option_list + (
        make_option('--add-permission',
            dest='add-permission',
            help="Add user permission"),
        make_option('--delete-permission',
            dest='delete-permission',
            help="Delete user permission"),
        make_option('--enable',
            action='store_true',
            dest='enable',
            default=False,
            help="Enable group"),
    )
    
    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("Please provide a group identifier")
        
        group = None
        try:
            if args[0].isdigit():
                group = AstakosGroup.objects.get(id=args[0])
            else:
                group = AstakosGroup.objects.get(name=args[0])
        except AstakosGroup.DoesNotExist, e:
            raise CommandError("Invalid group")
        
        try:
            pname = options.get('add-permission')
            if pname:
                r, created = add_group_permission(group, pname)
                if created:
                    self.stdout.write('Permission: %s created successfully\n' % pname)
                if r == 0:
                    self.stdout.write('Group has already permission: %s\n' % pname)
                else:
                    self.stdout.write('Permission: %s added successfully\n' % pname)
            
            pname = options.get('delete-permission')
            if pname:
                r = remove_group_permission(group, pname)
                if r < 0:
                    self.stdout.write('Invalid permission codename: %s\n' % pname)
                elif r == 0:
                    self.stdout.write('Group has not permission: %s\n' % pname)
                elif r > 0:
                    self.stdout.write('Permission: %s removed successfully\n' % pname)
            
            if options.get('enable'):
                group.enable()
        except Exception, e:
            raise CommandError(e)