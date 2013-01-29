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

from astakos.im.models import sync_projects

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Check for pending project synchronization"

    option_list = BaseCommand.option_list + (
        make_option('--check',
                    action='store_true',
                    dest='check',
                    default=True,
                    help="Check if projects are in sync with quotaholder (default)"),
        make_option('--trigger',
                    action='store_true',
                    dest='trigger',
                    default=False,
                    help="Sync projects to quotaholder"),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        trigger = options['trigger']

        try:
            log = sync_projects(sync=trigger)
            pending, (modified, reactivating, deactivating) = log

            if pending:
                self.stdout.write("Memberships pending sync:\n")
                for m in pending:
                    self.stdout.write("%s\n" % (m))
                self.stdout.write("\n")

            if modified:
                self.stdout.write("Modified projects:\n")
                for p in modified:
                    self.stdout.write("%s\n" % (p))
                self.stdout.write("\n")

            if reactivating:
                self.stdout.write("Reactivating projects:\n")
                for p in reactivating:
                    self.stdout.write("%s\n" % (p))
                self.stdout.write("\n")

            if deactivating:
                self.stdout.write("Deactivating projects:\n")
                for p in deactivating:
                    self.stdout.write("%s\n" % (p))
                self.stdout.write("\n")

        except BaseException, e:
            logger.exception(e)
            raise CommandError("Syncing failed.")
