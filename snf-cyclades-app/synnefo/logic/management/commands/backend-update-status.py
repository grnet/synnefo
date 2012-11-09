# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.
#

from optparse import make_option
from django.core.management.base import BaseCommand
from synnefo.management.common import get_backend

from synnefo import settings
import datetime

from synnefo.db.models import Backend
from synnefo.logic.backend import update_resources


class Command(BaseCommand):
    can_import_settings = True

    help = "Update backend statistics, which are used for instance allocation."
    output_transaction = True  # The management command runs inside
                               # an SQL transaction
    option_list = BaseCommand.option_list + (
        make_option('--backend-id', dest='backend_id',
                   help="Update statistics of only this backend"),
        make_option('--older-than', dest='older_than', metavar="MINUTES",
                   help="Update only backends that have not been updated for\
                   MINUTES. Set to 0 to force update."),
        make_option('--include-drained', dest='drained',
                    default=False,
                    action='store_true',
                    help="Also update statistics of drained backends")
        )

    def handle(self, **options):

        if options['backend_id']:
            backends = [get_backend(options['backend_id'])]
        else:
            backends = Backend.objects.filter(offline=False)
            if not options['drained']:
                backends = backends.filter(drained=False)

        now = datetime.datetime.now()
        if options['older_than'] is not None:
            minutes = int(options['older_than'])
        else:
            minutes = settings.BACKEND_REFRESH_MIN

        delta = datetime.timedelta(minutes=minutes)

        for b in backends:
            if now > b.updated + delta:
                update_resources(b)
                print 'Successfully updated backend with id: %d' % b.id
            else:
                print 'Backend %d does not need update' % b.id
