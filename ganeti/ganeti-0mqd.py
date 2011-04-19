#!/usr/bin/env python
#
# Copyright (c) 2010 Greek Research and Technology Network
#
"""Ganeti notification daemon for 0mqd

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

import zmq
import time
import json
import logging
import pyinotify
import daemon
import daemon.pidlockfile
from signal import signal, SIGINT, SIGTERM

from threading import Thread, Event, currentThread

from ganeti import utils
from ganeti import jqueue
from ganeti import constants
from ganeti import serializer


class StoppableThread(Thread):
    """Thread class with a stop() method.

    The thread needs to check regularly for the stopped() condition.
    When it does, it exits, so that another thread may .join() it.

    """
    def __init__(self, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)
        self._stop = Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


class GanetiZMQThread(StoppableThread):
    """The 0mq processing thread: PULLs and then PUBlishes notifications.

    This thread runs until stopped, receiving notifications over a
    0mq PULL socket, and publishing them over a 0mq PUB socket.

    The are currently two sources of notifications:
    a. ganeti-0mqd itself, monitoring the Ganeti job queue
    b. hooks running in the context of Ganeti

    """
    def __init__(self, logger, puller, publisher):
        StoppableThread.__init__(self)
        self.logger = logger
        self.puller = puller
        self.publisher = publisher

    def run(self):
        self.logger.debug("0mq thread ready")
        try:
            while True:
                # Pull
                self.logger.debug("Waiting on the 0mq PULL socket")
                data = self.puller.recv()
                self.logger.debug("Received message on 0mq PULL socket")
                if currentThread().stopped():
                    self.logger.debug("Thread has been stopped, leaving request loop")
                    return
                try:
                    msg = json.loads(data)
                    if msg['type'] not in ('ganeti-op-status'):
                        self.logger.error("Not forwarding message of unknown type: %s", msg.dumps(data))
                        continue
                except Exception, e:
                    self.logger.exception("Unexpected Exception decoding msg: %s", data)
                    continue

                # Publish
                self.logger.debug("PUBlishing msg: %s", json.dumps(msg))
                self.publisher.send_json(msg)

        except:
            self.logger.exception("Caught exception, terminating")
            os.kill(os.getpid(), SIGTERM)


class JobFileHandler(pyinotify.ProcessEvent):
    def __init__(self, logger, pusher):
            pyinotify.ProcessEvent.__init__(self)
            self.logger = logger
            self.pusher = pusher
                  
    def process_IN_CLOSE_WRITE(self, event):
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
            
            # Push to the 0mq thread for PUBlication
            self.logger.debug("PUSHing msg: %s", json.dumps(msg))
            self.pusher.send_json(msg)


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
                      default=settings.GANETI_0MQD_LOG_FILE,
                      metavar="FILE",
                      help="Write log to FILE instead of %s" %
                      settings.GANETI_0MQD_LOG_FILE),
    parser.add_option('--pid-file', dest="pid_file",
                      default=settings.GANETI_0MQD_PID_FILE,
                      metavar='PIDFILE',
                      help="Save PID to file (default: %s)" %
                      settings.GANETI_0MQD_PID_FILE)
    parser.add_option("-p", "--pull-port", dest="pull_port",
                      default=settings.GANETI_0MQD_PULL_PORT, type="int", metavar="PULL_PORT",
                      help="The TCP port number to use for the 0mq PULL endpoint")
    parser.add_option("-P", "--pub-port", dest="pub_port",
                      default=settings.GANETI_0MQD_PUB_PORT, type="int", metavar="PUB_PORT",
                      help="The TCP port number to use for the 0mq PUB endpoint")

    return parser.parse_args(args)

def main():
    global handler_logger

    (opts, args) = parse_arguments(sys.argv[1:])

    # The 0mq endpoints to use for receiving and publishing notifications.
    GANETI_0MQD_PUB_ENDPOINT = "tcp://*:%d" % int(opts.pub_port)
    GANETI_0MQD_PULL_ENDPOINT = "tcp://*:%d" % int(opts.pull_port)
    GANETI_0MQD_INPROC_ENDPOINT = "inproc://ganeti-0mqd"

    # Create pidfile
    pidf = daemon.pidlockfile.TimeoutPIDLockFile(
        opts.pid_file, 10)

    # Initialize logger
    lvl = logging.DEBUG if opts.debug else logging.INFO
    logger = logging.getLogger("ganeti-0mqd")
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

    # Create 0mq sockets: One for the PUBlisher, one for the PULLer,
    # one inproc PUSHer for inter-thread communication.
    zmqc = zmq.Context()
    puller = zmqc.socket(zmq.PULL)
    puller.bind(GANETI_0MQD_PULL_ENDPOINT)
    puller.bind(GANETI_0MQD_INPROC_ENDPOINT)
    
    publisher = zmqc.socket(zmq.PUB)
    publisher.bind(GANETI_0MQD_PUB_ENDPOINT)
  
    pusher = zmqc.socket(zmq.PUSH)
    pusher.connect(GANETI_0MQD_INPROC_ENDPOINT)
    logger.info("PUSHing to %s", GANETI_0MQD_INPROC_ENDPOINT)
    logger.info("PULLing from (%s, %s)",
        GANETI_0MQD_PULL_ENDPOINT, GANETI_0MQD_INPROC_ENDPOINT)
    logger.info("PUBlishing on %s", GANETI_0MQD_PUB_ENDPOINT)

    # Use a separate thread for 0mq processing,
    # needed because the Python runtime interacts badly with 0mq's blocking semantics.
    zmqt = GanetiZMQThread(logger, puller, publisher)
    zmqt.start()

    # Monitor the Ganeti job queue, create and push notifications
    wm = pyinotify.WatchManager()
    mask = pyinotify.EventsCodes.ALL_FLAGS["IN_CLOSE_WRITE"]
    handler = JobFileHandler(logger, pusher)
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
        # mark the 0mq thread as stopped, wake it up so that it notices
        zmqt.stop()
        pusher.send_json({'type': 'null'})
        raise


if __name__ == "__main__":
    sys.exit(main())

# vim: set ts=4 sts=4 sw=4 et ai :
