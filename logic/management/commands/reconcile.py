# Copyright 2011 GRNET S.A. All rights reserved.
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
# Reconcile VM state - Management Script


from django.core.management.base import NoArgsCommand
from synnefo.db.models import VirtualMachine
from django.conf import settings
from datetime import datetime, timedelta

from synnefo.logic import amqp_connection
from synnefo.logic.amqp_connection import AMQPError

import json
import sys

class Command(NoArgsCommand):
    help = 'Reconcile VM status with the backend'

    def handle_noargs(self, **options):

        now = datetime.now()
        last_update = timedelta(minutes = settings.RECONCILIATION_MIN)
        not_updated = VirtualMachine.objects \
                                    .filter(deleted = False) \
                                    .filter(suspended = False) \
                                    .filter(updated__lte = (now - last_update))
        all =  VirtualMachine.objects.all()

        to_update = all.count() / settings.RECONCILIATION_MIN
        vm_ids = map(lambda x: x.id, not_updated[:to_update])

        for vmid in vm_ids :
            msg = dict(type = "reconcile", vmid = vmid)
            try:
                amqp_connection.send(json.dumps(msg), settings.EXCHANGE_CRON,
                                 "reconciliation.%s"%vmid)
            except AMQPError as e:
                print >> sys.stderr, 'Error sending reconciliation request: %s' % e
                raise

        print "All: %d, To update: %d, Triggered update for: %s" % \
              (all.count(), not_updated.count(), vm_ids)
