#!/usr/bin/env python
#
# Copyright (c) 2011 Greek Research and Technology Network
#
"""Connect to a queue 

This daemon receives job notifications from a number of queues


"""

from django.core.management import setup_environ

import sys
import os
path = os.path.normpath(os.path.join(os.getcwd(), '..'))
sys.path.append(path)
import synnefo.settings as settings

setup_environ(settings)

from amqplib import client_0_8 as amqp

from signal import signal, SIGINT, SIGTERM

import logging
import time
import socket

from synnefo.logic import dispatcher_callbacks

# List of worker ids
global children

class Dispatcher:

    logger = None
    chan = None
    debug = False
    clienttags = []

    def __init__(self, debug = False, logger = None):
        self.logger = logger
        self.debug = debug
        self._init()

    def wait(self):
        while True:
            try:
                self.chan.wait()
            except SystemExit:
                break
            except socket.error:
                self.logger.error("Server went away, reconnecting...")
                self._init()
                pass

        [self.chan.basic_cancel(clienttag) for clienttag in self.clienttags]
        self.chan.close()
        self.chan.connection.close()
        sys.exit()

    def _init(self):
        # Connect to RabbitMQ
        conn = None
        while conn == None:
            self.logger.info("Attempting to connect to %s",
                             settings.RABBIT_HOST)
            try:
                conn = amqp.Connection(host=settings.RABBIT_HOST,
                                       userid=settings.RABBIT_USERNAME,
                                       password=settings.RABBIT_PASSWORD,
                                       virtual_host=settings.RABBIT_VHOST)
            except socket.error:
                time.sleep(1)
                pass

        self.logger.info("Connection succesful, opening channel")
        self.chan = conn.channel()

        # Declare queues and exchanges
        for exchange in settings.EXCHANGES:
            self.chan.exchange_declare(exchange=exchange, type="topic",
                                       durable=True, auto_delete=False)

        for queue in settings.QUEUES:
            self.chan.queue_declare(queue=queue, durable=True,
                                    exclusive=False, auto_delete=False)

        bindings = settings.BINDINGS

        # Special queue for debugging, should not appear in production
        if self.debug:
            self.chan.queue_declare(queue=settings.QUEUE_DEBUG, durable=True,
                                    exclusive=False, auto_delete=False)
            bindings += settings.BINDINGS_DEBUG

        # Bind queues to handler methods
        for binding in bindings:
            try:
                cb = getattr(dispatcher_callbacks, binding[3])
            except AttributeError:
                self.logger.error("Cannot find callback %s" % binding[3])
                continue

            self.chan.queue_bind(queue=binding[0], exchange=binding[1],
                                 routing_key=binding[2])
            tag = self.chan.basic_consume(queue=binding[0], callback=cb)
            self.logger.debug("Binding %s(%s) to queue %s with handler %s" %
                              (binding[1], binding[2], binding[0], binding[3]))
            self.clienttags.append(tag)


def _exit_handler(signum, frame):
    """"Catch exit signal in children processes."""
    print "%d: Caught signal %d, will raise SystemExit" % (os.getpid(),signum)
    raise SystemExit


def _parent_handler(signum, frame):
    """"Catch exit signal in parent process and forward it to children."""
    global children
    print "Caught signal %d, sending kill signal to children" % signum
    [os.kill(pid, SIGTERM) for pid in children]


def child(cmdline, logger):
    """The context of the child process"""

    # Cmd line argument parsing
    (opts, args) = parse_arguments(cmdline)
    d = Dispatcher(debug = opts.debug, logger = logger)

    # Start the event loop
    d.wait()


def parse_arguments(args):
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-d", "--debug", action="store_true", default=False,
                      dest="debug",
            help="Enable debug mode")
    parser.add_option("-l", "--log", dest="log_file",
            default=settings.DISPATCHER_LOG_FILE,
            metavar="FILE",
            help="Write log to FILE instead of %s" %
            settings.DISPATCHER_LOG_FILE)
    parser.add_option("-c", "--cleanup-queues", action="store_true",
                      default=False, dest="cleanup_queues",
            help="Remove all queues declared in settings.py (DANGEROUS!)")
    parser.add_option("-w", "--workers", default=2, dest="workers",
            help="Number of workers to spawn", type="int")
    
    return parser.parse_args(args)


def cleanup_queues() :
    """Delete declared queues from RabbitMQ. Use with care!"""
    conn = amqp.Connection( host=settings.RABBIT_HOST,
                            userid=settings.RABBIT_USERNAME,
                            password=settings.RABBIT_PASSWORD,
                            virtual_host=settings.RABBIT_VHOST)
    chan = conn.channel()

    print "Queues to be deleted: ",  settings.QUEUES
    print "Exchnages to be deleted: ", settings.EXCHANGES
    ans = raw_input("Are you sure (N/y):")

    if not ans:
        return
    if ans not in ['Y', 'y']:
        return

    #for exchange in settings.EXCHANGES:
    #    try:
    #        chan.exchange_delete(exchange=exchange)
    #    except amqp.exceptions.AMQPChannelException as e:
    #        print e.amqp_reply_code, " ", e.amqp_reply_text

    for queue in settings.QUEUES:
        try:
            chan.queue_delete(queue=queue)
        except amqp.exceptions.AMQPChannelException as e:
            print e.amqp_reply_code, " ", e.amqp_reply_text
    chan.close()
    chan.connection.close()


def main():
    global children, logger
    (opts, args) = parse_arguments(sys.argv[1:])

    # Initialize logger
    lvl = logging.DEBUG if opts.debug else logging.INFO
    logger = logging.getLogger("synnefo.dispatcher")
    logger.setLevel(lvl)
    formatter = logging.Formatter(
            "%(asctime)s %(module)s[%(process)d] %(levelname)s: %(message)s",
            "%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(opts.log_file)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Special case for the clean up queues action
    if opts.cleanup_queues:
        cleanup_queues()
        return

    # Fork workers
    children = []

    i = 0
    while i < opts.workers:
        newpid = os.fork()

        if newpid == 0:
            signal(SIGINT, _exit_handler)
            signal(SIGTERM, _exit_handler)
            child(sys.argv[1:], logger)
            sys.exit(0)
        else:
            pids = (os.getpid(), newpid)
            logger.debug("%d, forked child: %d" % pids)
            children.append(pids[1])
        i += 1

    # Catch signals to ensure graceful shutdown
    signal(SIGINT,  _parent_handler)
    signal(SIGTERM, _parent_handler)

    # Wait for all children process to die, one by one
    for c in children:
        try:
            os.wait()
        except Exception:
            pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
