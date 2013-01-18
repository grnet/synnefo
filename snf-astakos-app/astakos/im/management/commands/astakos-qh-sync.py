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
from django.db import transaction

from astakos.im.models import sync_all_users, sync_projects

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Inspect quotaholder status and sync"

    option_list = BaseCommand.option_list + (
        make_option('--users',
                    action='store_true',
                    dest='users',
                    default=False,
                    help="Check if users and their quotas are in sync with quotaholder"),
        make_option('--projects',
                    action='store_true',
                    dest='projects',
                    default=False,
                    help="Check if projects are in sync with quotaholder"),
        make_option('--execute',
                    action='store_true',
                    dest='execute',
                    default=False,
                    help="Perform the actual operation"),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        execute = options['execute']

        try:
            if options['users']:
                log = sync_all_users(execute=execute)
            elif options['projects']:
                log = sync_projects(execute=execute)
        except BaseException, e:
            logger.exception(e)
            raise CommandError("Syncing failed.")
