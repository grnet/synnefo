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

from synnefo.db.models import VirtualMachine

from ._common import format_bool, format_date


class Command(BaseCommand):
    args = "<server ID>"
    help = "Modify a server"
    
    option_list = BaseCommand.option_list + (
        make_option('--name',
            dest='name',
            metavar='NAME',
            help="Set server's name"),
        make_option('--owner',
            dest='owner',
            metavar='USER_ID',
            help="Set server's owner"),
        make_option('--state',
            dest='state',
            metavar='STATE',
            help="Set server's state"),
        make_option('--set-deleted',
            action='store_true',
            dest='deleted',
            help="Mark a server as deleted"),
        make_option('--set-undeleted',
            action='store_true',
            dest='undeleted',
            help="Mark a server as not deleted"),
        make_option('--set-suspended',
            action='store_true',
            dest='suspended',
            help="Mark a server as suspended"),
        make_option('--set-unsuspended',
            action='store_true',
            dest='unsuspended',
            help="Mark a server as not suspended")
        )
    
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a server ID")
        
        try:
            server_id = int(args[0])
            server = VirtualMachine.objects.get(id=server_id)
        except (ValueError, VirtualMachine.DoesNotExist):
            raise CommandError("Invalid server ID")
        
        name = options.get('name')
        if name is not None:
            server.name = name
        
        owner = options.get('owner')
        if owner is not None:
            server.userid = owner
        
        state = options.get('state')
        if state is not None:
            allowed = [x[0] for x in VirtualMachine.OPER_STATES]
            if state not in allowed:
                msg = "Invalid state, must be one of %s" % ', '.join(allowed)
                raise CommandError(msg)
            server.operstate = state
        
        if options.get('deleted'):
            server.deleted = True
        elif options.get('undeleted'):
            server.deleted = False
        
        if options.get('suspended'):
            server.suspended = True
        elif options.get('unsuspended'):
            server.suspended = False
        
        server.save()
