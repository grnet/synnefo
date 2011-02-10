#!/usr/bin/env python
#
# Copyright (c) 2010 Greek Research and Technology Network
#
"""Receive Ganeti events over 0mq, update VM state in DB.

This daemon receives job notifications from ganeti-0mqd
and updates VM state in the DB accordingly.

"""

from django.core.management import setup_environ

import sys
import os
path = os.path.normpath(os.path.join(os.getcwd(), '..'))
sys.path.append(path)
import settings

setup_environ(settings)

import sys
import zmq
import time
import json
import signal
import logging
import traceback

from threading import Thread

from synnefo.db.models import VirtualMachine

GANETI_ZMQ_PUBLISHER = "tcp://62.217.120.67:5801" # FIXME: move to settings.py

def zmq_sub_thread(subscriber):
    while True:
        #
        # This completely blocks any interrupts,
        # how do I asynchronously terminate the thread?
        #
        logging.debug("Entering 0mq to wait for message on SUB socket.")
        data = subscriber.recv()
        logging.debug("Received message on 0mq SUB socket.")
        try:
            msg = json.loads(data)

            if msg["type"] != "ganeti-op-status":
                logging.debug("Ignoring message of uknown type %s." % (msg["type"]))
                continue

            vmid = VirtualMachine.id_from_instance_name(msg["instance"])
            vm = VirtualMachine.objects.get(id=vmid)
    
            logging.debug("Processing msg: %s" % (msg))
            vm.process_backend_msg(msg["jobId"], msg["operation"], msg["status"], msg["logmsg"])
            vm.save()
            logging.debug("Done processing msg for vm %s." % (msg["instance"]))

        except KeyError:
            logging.error("Malformed incoming JSON, missing attributes: " + data)
        except VirtualMachine.InvalidBackendIdError:
            logging.debug("Ignoring msg for unknown instance %s." % msg["instance"])
        except VirtualMachine.DoesNotExist:
            logging.error("VM for instance %s with id %d not found in DB." % (msg["instance"], vmid))
        except Exception as e:
            logging.error("Unexpected error:\n" + "".join(traceback.format_exception(*sys.exc_info())))
            continue

def main():
    # Connect to ganeti-0mqd
    zmqc = zmq.Context()
    subscriber = zmqc.socket(zmq.SUB)
    subscriber.setsockopt(zmq.IDENTITY, "snf-db-controller")
    subscriber.setsockopt(zmq.SUBSCRIBE, "")
    subscriber.connect(GANETI_ZMQ_PUBLISHER)

    zmqt = Thread(target = zmq_sub_thread, args = (subscriber,))
    zmqt.start()

    try:
        while True:
            print "In main thread."
            time.sleep(0.5)
    except KeyboardInterrupt:
        print "OK, I'm barfing."
        # Do whatever clean-up may be necessary.
        # Gloriously commit seppuku.
        os.kill(os.getpid(), signal.SIGQUIT)
        # These don't seem to work, must find out way.
        # In general, they seem to want to join the I/O thread, which blocks forever.
        raise SystemExit()
        sys.exit(1)
        
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())

# vim: set ts=4 sts=4 sw=4 et ai :
