#!/usr/bin/env python
#
# Copyright (c) 2010 Greek Research and Technology Network
#
"""Ganeti notification daemon with amqp 

A daemon to monitor the Ganeti job queue and publish job progress
and Ganeti VM state notifications over a 0mq PUB endpoint.

"""

from django.core.management import setup_environ

import sys
import os
path = os.path.normpath(os.path.join(os.getcwd(), '..'))
sys.path.append(path)
import synnefo.settings as settings

setup_environ(settings)

import time
import json
import logging
import pyinotify
import daemon
import daemon.pidlockfile
import socket
from signal import signal, SIGINT, SIGTERM

from amqplib import client_0_8 as amqp

from threading import Thread, Event, currentThread

from ganeti import utils
from ganeti import jqueue
from ganeti import constants
from ganeti import serializer

class JobFileHandler(pyinotify.ProcessEvent):
    def __init__(self, logger):
        pyinotify.ProcessEvent.__init__(self)
        self.logger = logger
        self.chan = None 

    def open_channel(self):
        conn = None
        while conn == None:
            handler_logger.info("Attempting to connect to %s", settings.RABBIT_HOST)
            try:
                conn = amqp.Connection( host=settings.RABBIT_HOST,
                     userid=settings.RABBIT_USERNAME,
                     password=settings.RABBIT_PASSWORD,
                     virtual_host=settings.RABBIT_VHOST)
            except socket.error:
                time.sleep(1)
                pass
        
        handler_logger.info("Connection succesful, opening channel")
        return conn.channel()

    def process_IN_CLOSE_WRITE(self, event):
        if self.chan == None:
            self.chan = self.open_channel()

        jobfile = os.path.join(event.path, event.name)
        if not event.name.startswith("job-"):
            self.logger.debug("Not a job file: %s" % event.path)
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

            self.logger.debug("%d: %s(%s) %s %s",
                    int(job.id), op.input.OP_ID, instances, op.status, logmsg)

            # Construct message
            msg = {
                    "type": "ganeti-op-status",
                    "instance": instances,
                    "operation": op.input.OP_ID,
                    "jobId": int(job.id),
                    "status": op.status,
                    "logmsg": logmsg
                    }
            if logmsg:
                msg["message"] = logmsg

            self.logger.debug("PUSHing msg: %s", json.dumps(msg))
            msg = amqp.Message(json.dumps(msg))
            msg.properties["delivery_mode"] = 2 #Persistent
            try:    
                self.chan.basic_publish(msg,exchange="ganeti",routing_key="eventd")
            except socket.error:
                self.logger.error("Server went away, reconnecting...")
                self.chan = self.open_channel()
                self.chan.basic_publish(msg,exchange="ganeti",routing_key="eventd")
            except Exception:
                self.logger.error("Uknown error (msg: %s)", msg)
                raise

handler_logger = None
def fatal_signal_handler(signum, frame):
    global handler_logger

    handler_logger.info("Caught fatal signal %d, will raise SystemExit",
            signum)
    raise SystemExit

def parse_arguments(args):
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-d", "--debug", action="store_true", dest="debug",
            help="Enable debugging information")
    parser.add_option("-l", "--log", dest="log_file",
            default=settings.GANETI_EVENTD_LOG_FILE,
            metavar="FILE",
            help="Write log to FILE instead of %s" %
            settings.GANETI_EVENTD_LOG_FILE),
    parser.add_option('--pid-file', dest="pid_file",
            default=settings.GANETI_EVENTD_PID_FILE,
            metavar='PIDFILE',
            help="Save PID to file (default: %s)" %
            settings.GANETI_EVENTD_PID_FILE)

    return parser.parse_args(args)

def main():
    global handler_logger

    (opts, args) = parse_arguments(sys.argv[1:])

    # Create pidfile
    pidf = daemon.pidlockfile.TimeoutPIDLockFile(opts.pid_file, 10)

    # Initialize logger
    lvl = logging.DEBUG if opts.debug else logging.INFO
    logger = logging.getLogger("ganeti-amqpd")
    logger.setLevel(lvl)
    formatter = logging.Formatter("%(asctime)s %(module)s[%(process)d] %(levelname)s: %(message)s",
            "%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(opts.log_file)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    handler_logger = logger

    # Become a daemon:
    # Redirect stdout and stderr to handler.stream to catch
    # early errors in the daemonization process [e.g., pidfile creation]
    # which will otherwise go to /dev/null.
    daemon_context = daemon.DaemonContext(
            pidfile=pidf,
            umask=022,
            stdout=handler.stream,
            stderr=handler.stream,
            files_preserve=[handler.stream])
    daemon_context.open()
    logger.info("Became a daemon")

    # Catch signals to ensure graceful shutdown
    signal(SIGINT, fatal_signal_handler)
    signal(SIGTERM, fatal_signal_handler)

    # Monitor the Ganeti job queue, create and push notifications
    wm = pyinotify.WatchManager()
    mask = pyinotify.EventsCodes.ALL_FLAGS["IN_CLOSE_WRITE"]
    handler = JobFileHandler(logger)
    notifier = pyinotify.Notifier(wm, handler)

    try:
        # Fail if adding the inotify() watch fails for any reason
        res = wm.add_watch(constants.QUEUE_DIR, mask)
        if res[constants.QUEUE_DIR] < 0:
            raise Exception("pyinotify add_watch returned negative watch descriptor")

        logger.info("Now watching %s" % constants.QUEUE_DIR)

        while True:    # loop forever
            # process the queue of events as explained above
            notifier.process_events()
            if notifier.check_events():
                # read notified events and enqeue them
                notifier.read_events()
    except SystemExit:
        logger.info("SystemExit")
    except:
        logger.exception("Caught exception, terminating")
    finally:
        # destroy the inotify's instance on this interrupt (stop monitoring)
        notifier.stop()
        raise

if __name__ == "__main__":
    sys.exit(main())

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
