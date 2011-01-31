#!/usr/bin/env python
#
# Copyright (c) 2010 Greek Research and Technology Network
#
""" A daemon to monitor the Ganeti job queue and emit job progress notifications over 0mq. """

import os
import sys
import zmq
import time
import json
import logging
import pyinotify

from ganeti import utils
from ganeti import jqueue
from ganeti import constants
from ganeti import serializer

GANETI_ZMQ_PUBLISHER = "tcp://*:5801" # FIXME: move to settings.py


class JobFileHandler(pyinotify.ProcessEvent):
    def __init__(self, publisher):
            pyinotify.ProcessEvent.__init__(self)
            self.publisher = publisher
                  
    def process_IN_CLOSE_WRITE(self, event):
        jobfile = os.path.join(event.path, event.name)
        if not event.name.startswith("job-"):
            logging.debug("Not a job file: %s" % event.path)
            return

        try:
            data = utils.ReadFile(jobfile)
        except IOError:

            return

        data = serializer.LoadJson(data)
        job = jqueue._QueuedJob.Restore(None, data)

        for op in job.ops:
            instances = ""
            try:
                instances = " ".join(op.input.instances)
            except AttributeError:
                pass

            try:
                instances = op.input.instance_name
            except AttributeError:
                pass

            # Get the last line of the op log as message
            try:
                logmsg = op.log[-1][-1]
            except IndexError:
                logmsg = None
            
            logging.debug("%d: %s(%s) %s %s" % (int(job.id), op.input.OP_ID, instances, op.status, logmsg))
            if op.status in constants.JOBS_FINALIZED:
                logging.info("%d: %s" % (int(job.id), op.status))

            # Construct message
            msg = {
                "type": "Ganeti-op-status",
                "instance": instances,
                "operation": op.input.OP_ID,
                "jobId": int(job.id),
                "status": op.status
            }
            if logmsg:
                msg["message"] = logmsg
            
            # Output as JSON
            print json.dumps(msg)
            
            self.publisher.send_json(msg)


def main():
    zmqc = zmq.Context()
    publisher = zmqc.socket(zmq.PUB)
    publisher.bind(GANETI_ZMQ_PUBLISHER)
    logging.info("Now publishing on %s" % GANETI_ZMQ_PUBLISHER)
    
    wm = pyinotify.WatchManager()
    mask = pyinotify.EventsCodes.ALL_FLAGS["IN_CLOSE_WRITE"]
    handler = JobFileHandler(publisher)
    notifier = pyinotify.Notifier(wm, handler)
    wm.add_watch(constants.QUEUE_DIR, mask)

    logging.info("Now watching %s" % constants.QUEUE_DIR)

    while True:    # loop forever
        try:
            # process the queue of events as explained above
            notifier.process_events()
            if notifier.check_events():
                # read notified events and enqeue them
                notifier.read_events()
        except KeyboardInterrupt:
            # destroy the inotify's instance on this interrupt (stop monitoring)
            notifier.stop()
            break


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())

# vim: set ts=4 sts=4 sw=4 et ai :
