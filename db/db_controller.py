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
import synnefo.settings as settings

setup_environ(settings)

import zmq
import time
import json
import platform
import logging
import getpass
import traceback

from threading import Thread, Event, currentThread

from synnefo.db.models import VirtualMachine

GANETI_ZMQ_PUBLISHER = "tcp://62.217.120.67:5801" # FIXME: move to settings.py

class StoppableThread(Thread):
    """Thread class with a stop() method.
    
    The thread needs to check regularly for the stopped() condition.
    When it does, it exits, so that another thread may .join() it.

    """

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop = Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


def zmq_sub_thread(subscriber):
    while True:
        logging.debug("Entering 0mq to wait for message on SUB socket.")
        data = subscriber.recv()
        logging.debug("Received message on 0mq SUB socket.")
        try:
            msg = json.loads(data)

            if currentThread().stopped():
                logging.debug("Thread has been stopped, leaving request loop.")
                return

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
    # Create an inproc PUB socket, for inter-thread communication
    zmqc = zmq.Context()
    inproc = zmqc.socket(zmq.PUB)
    inproc.bind("inproc://threads")

    #
    # Create a SUB socket, connect to ganeti-0mqd and the inproc PUB socket
    #
    subscriber = zmqc.socket(zmq.SUB)

    # Combine the hostname, username and a constant string to get
    # a hopefully unique identity for this 0mq peer.
    # Reusing zmq.IDENTITY for two distinct peers triggers this 0mq bug:
    # https://github.com/zeromq/zeromq2/issues/30
    subscriber.setsockopt(zmq.IDENTITY, platform.node() + getpass.getuser() + "snf-db-controller")
    subscriber.setsockopt(zmq.SUBSCRIBE, "")
    subscriber.connect(GANETI_ZMQ_PUBLISHER)
    subscriber.connect("inproc://threads")

    # Use a separate thread to process incoming messages,
    # needed because the Python runtime interacts badly with 0mq's blocking semantics.
    zmqt = StoppableThread(target = zmq_sub_thread, args = (subscriber,))
    zmqt.start()

    try:
        logging.info("in main thread.");
        while True:
            logging.info("When I grow up, I'll be syncing with Ganeti at this point.")
            time.sleep(600)
    except:
        logging.error("Caught exception:\n" + "".join(traceback.format_exception(*sys.exc_info())))
        
        #
        # Cleanup.
        #
        # Cancel the suscriber thread, wake it up, then join it.
        zmqt.stop()
        inproc.send_json({"type":"null"})
        zmqt.join()

        return 1

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())

# vim: set ts=4 sts=4 sw=4 et ai :
