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

from amqplib import client_0_8 as amqp

import time
import socket
import json

class Command(NoArgsCommand):
    help = 'Reconcile VM status with the backend'
    chan = None
    def open_channel(self):
        conn = None
        while conn == None:
            try:
                conn = amqp.Connection( host=settings.RABBIT_HOST,
                     userid=settings.RABBIT_USERNAME,
                     password=settings.RABBIT_PASSWORD,
                     virtual_host=settings.RABBIT_VHOST)
            except socket.error:
                time.sleep(1)
                pass

        self.chan = conn.channel()

    def handle_noargs(self, **options):

        now = datetime.now()
        last_update = timedelta(minutes = 30)
        not_updated = VirtualMachine.objects.filter(updated__lte = (now - last_update))
        all =  VirtualMachine.objects.all()

        to_update = all.count() / settings.RECONCILIATION_MIN

        vm_ids = map(lambda x: x.id,  VirtualMachine.objects.all()[:to_update])
        sent = False
        self.open_channel()
        for vmid in vm_ids :
            while sent is False:
                try:
                    msg = dict(type = "reconcile", vmid = vmid)
                    amqp_msg = amqp.Message(json.dumps(msg))
                    self.chan.basic_publish(amqp_msg,
                            exchange=settings.EXCHANGE_CRON,
                            routing_key="reconciliation.%s"%vmid)
                    sent = True
                except socket.error:
                    self.chan = self.open_channel()
                except Exception:
                    raise

        print "All: %d, To update: %d, Triggered update for: %s" % (all.count(), not_updated.count(), vm_ids)
