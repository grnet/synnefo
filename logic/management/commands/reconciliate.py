#
# Reconciliate VM state - Management Script
#
# Copyright 2010 Greek Research and Technology Network
#

from django.core.management.base import NoArgsCommand
from synnefo.db.models import VirtualMachine
from django.conf import settings
from datetime import datetime, timedelta

from amqplib import client_0_8 as amqp

import time
import socket
import json

class Command(NoArgsCommand):
    help = 'Reconciliate VM status with the backend'

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

        return conn.channel()

    def handle_noargs(self, **options):

        now = datetime.now()
        last_update = timedelta(minutes = 30)
        not_updated = VirtualMachine.objects.filter(updated__lte = (now - last_update))
        all =  VirtualMachine.objects.all()

        to_update = all.count() / settings.RECONCILIATION_MIN

        vm_ids = map(lambda x: x.vm_id,  all.filter()) #TODO: Fix filtering
        sent = False

        for vmid in vm_ids :
            while sent is False:
                try:
                    msg = dict(type = "reconciliate", vmid = vmid)
                    self.chan.basic_publish(json.dumps(msg),
                            exchange=settings.EXCHANGE_CRON,
                            routing_key="reconciliation.%s", vmid)
                    sent = True
                except socket.error:
                    self.chan = self.open_channel()
                except Exception:
                    raise


        print "All:%d, Not Updated:%d, Triggered update for:%d" % (all.count(), not_updated.count(), vm_ids)
