#!/usr/bin/env python
#
# Copyright (c) 2010 Greek Research and Technology Network
#
""" Receive Ganeti events over 0mq """

import sys
import zmq
import time
import json
import logging

GANETI_ZMQ_PUBLISHER = "tcp://ganeti-master:5801" # FIXME: move to settings.py

def main():
    # Connect to ganeti-0mqd
    zmqc = zmq.Context()
    subscriber = zmqc.socket(zmq.SUB)
    subscriber.setsockopt(zmq.IDENTITY, "DBController")
    subscriber.setsockopt(zmq.SUBSCRIBE, "")
    subscriber.connect(GANETI_ZMQ_PUBLISHER)

    print "Connected to %s." % GANETI_ZMQ_PUBLISHER

    # Get updates, expect random Ctrl-C death
    while True:
        data = subscriber.recv()
        print data

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())

# vim: set ts=4 sts=4 sw=4 et ai :
