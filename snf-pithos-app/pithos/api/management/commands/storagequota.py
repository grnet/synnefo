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

from pithos.api.settings import (BACKEND_DB_MODULE, BACKEND_DB_CONNECTION,
                                    BACKEND_BLOCK_MODULE, BACKEND_BLOCK_PATH,
                                    BACKEND_BLOCK_UMASK,
                                    BACKEND_QUEUE_MODULE, BACKEND_QUEUE_CONNECTION,
                                    BACKEND_QUOTA, BACKEND_VERSIONING)
from pithos.backends import connect_backend


class Command(BaseCommand):
    args = "<user>"
    help = "Get/set a user's quota"
    
    option_list = BaseCommand.option_list + (
        make_option('--set-quota',
            dest='quota',
            metavar='BYTES',
            help="Set user's quota"),
        )
    
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a user")
        
        user = args[0]
        quota = options.get('quota')
        if quota is not None:
            try:
                quota = int(quota)
            except ValueError:
                raise CommandError("Invalid quota")
        
        backend = connect_backend(db_module=BACKEND_DB_MODULE,
                                  db_connection=BACKEND_DB_CONNECTION,
                                  block_module=BACKEND_BLOCK_MODULE,
                                  block_path=BACKEND_BLOCK_PATH,
                                  block_umask=BACKEND_BLOCK_UMASK,
                                  queue_module=BACKEND_QUEUE_MODULE,
                                  queue_connection=BACKEND_QUEUE_CONNECTION)
        backend.default_policy['quota'] = BACKEND_QUOTA
        backend.default_policy['versioning'] = BACKEND_VERSIONING
        if quota is not None:
            backend.update_account_policy(user, user, {'quota': quota})
        else:
            self.stdout.write("Quota for %s: %s\n" % (user, backend.get_account_policy(user, user)['quota']))
        backend.close()
