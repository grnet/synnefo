#!/usr/bin/env python
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


""" Message queue setup, dispatch and admin

This program sets up connections to the queues configured in settings.py
and implements the message wait and dispatch loops. Actual messages are
handled in the dispatched functions.

"""
from django.core.management import setup_environ

import sys
import os
path = os.path.normpath(os.path.join(os.getcwd(), '..'))
sys.path.append(path)
import synnefo.settings as settings
from synnefo.logic import log

setup_environ(settings)

from amqplib import client_0_8 as amqp
from signal import signal, SIGINT, SIGTERM

import time
import socket
from daemon import daemon

import traceback

# Take care of differences between python-daemon versions.
try:
    from daemon import pidfile
except:
    from daemon import pidlockfile

from synnefo.logic import callbacks

# Queue names
QUEUES = []

# Queue bindings to exchanges
BINDINGS = []


class Dispatcher:

    logger = None
    chan = None
    debug = False
    clienttags = []

    def __init__(self, debug=False):

        # Initialize logger
        self.logger = log.get_logger('synnefo.dispatcher')

        self.debug = debug
        self._init()

    def wait(self):
        while True:
            try:
                self.chan.wait()
            except SystemExit:
                break
            except amqp.exceptions.AMQPConnectionException:
                self.logger.error("Server went away, reconnecting...")
                self._init()
            except socket.error:
                self.logger.error("Server went away, reconnecting...")
                self._init()
            except Exception, e:
                self.logger.exception("Caught unexpected exception")

        [self.chan.basic_cancel(clienttag) for clienttag in self.clienttags]
        self.chan.connection.close()
        self.chan.close()

    def _init(self):
        global QUEUES, BINDINGS
        self.logger.info("Initializing")

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
                self.logger.error("Failed to connect to %s, retrying in 10s",
                                  settings.RABBIT_HOST)
                time.sleep(10)

        self.logger.info("Connection succesful, opening channel")
        self.chan = conn.channel()

        # Declare queues and exchanges
        for exchange in settings.EXCHANGES:
            self.chan.exchange_declare(exchange=exchange, type="topic",
                                       durable=True, auto_delete=False)

        for queue in QUEUES:
            self.chan.queue_declare(queue=queue, durable=True,
                                    exclusive=False, auto_delete=False)

        bindings = BINDINGS

        # Bind queues to handler methods
        for binding in bindings:
            try:
                callback = getattr(callbacks, binding[3])
            except AttributeError:
                self.logger.error("Cannot find callback %s" % binding[3])
                raise SystemExit(1)

            self.chan.queue_bind(queue=binding[0], exchange=binding[1],
                                 routing_key=binding[2])
            tag = self.chan.basic_consume(queue=binding[0], callback=callback)
            self.logger.debug("Binding %s(%s) to queue %s with handler %s" %
                              (binding[1], binding[2], binding[0], binding[3]))
            self.clienttags.append(tag)


def _init_queues():
    global QUEUES, BINDINGS

    # Queue declarations
    prefix = settings.BACKEND_PREFIX_ID.split('-')[0]

    QUEUE_GANETI_EVENTS_OP = "%s-events-op" % prefix
    QUEUE_GANETI_EVENTS_NET = "%s-events-net" % prefix
    QUEUE_GANETI_BUILD_PROGR = "%s-events-progress" % prefix
    QUEUE_CRON_CREDITS = "%s-credits" % prefix
    QUEUE_EMAIL = "%s-email" % prefix
    QUEUE_RECONC = "%s-reconciliation" % prefix
    if settings.DEBUG is True:
        QUEUE_DEBUG = "debug"       # Debug queue, retrieves all messages

    QUEUES = (QUEUE_GANETI_EVENTS_OP, QUEUE_GANETI_EVENTS_NET,
              QUEUE_CRON_CREDITS, QUEUE_EMAIL, QUEUE_RECONC,
              QUEUE_GANETI_BUILD_PROGR)

    # notifications of type "ganeti-op-status"
    DB_HANDLER_KEY_OP = 'ganeti.%s.event.op' % prefix
    # notifications of type "ganeti-net-status"
    DB_HANDLER_KEY_NET = 'ganeti.%s.event.net' % prefix
    # notifications of type "ganeti-create-progress"
    BUILD_MONITOR_HANDLER = 'ganeti.%s.event.progress' % prefix
    # email
    EMAIL_HANDLER = 'logic.%s.email.*' % prefix
    # reconciliation
    RECONC_HANDLER = 'reconciliation.%s.*' % prefix

    BINDINGS = [
    # Queue                   # Exchange                # RouteKey              # Handler
    (QUEUE_GANETI_EVENTS_OP,  settings.EXCHANGE_GANETI, DB_HANDLER_KEY_OP,      'update_db'),
    (QUEUE_GANETI_EVENTS_NET, settings.EXCHANGE_GANETI, DB_HANDLER_KEY_NET,     'update_net'),
    (QUEUE_GANETI_BUILD_PROGR,settings.EXCHANGE_GANETI, BUILD_MONITOR_HANDLER,  'update_build_progress'),
    (QUEUE_CRON_CREDITS,      settings.EXCHANGE_CRON,   '*.credits.*',          'update_credits'),
    (QUEUE_EMAIL,             settings.EXCHANGE_API,    EMAIL_HANDLER,          'send_email'),
    (QUEUE_EMAIL,             settings.EXCHANGE_CRON,   EMAIL_HANDLER,          'send_email'),
    (QUEUE_RECONC,            settings.EXCHANGE_CRON,   RECONC_HANDLER,         'trigger_status_update'),
    ]

    if settings.DEBUG is True:
        BINDINGS += [
            # Queue       # Exchange          # RouteKey  # Handler
            (QUEUE_DEBUG, settings.EXCHANGE_GANETI, '#',  'dummy_proc'),
            (QUEUE_DEBUG, settings.EXCHANGE_CRON,   '#',  'dummy_proc'),
            (QUEUE_DEBUG, settings.EXCHANGE_API,    '#',  'dummy_proc'),
        ]
        QUEUES += (QUEUE_DEBUG,)


def _exit_handler(signum, frame):
    """"Catch exit signal in children processes"""
    global logger
    logger.info("Caught signal %d, will raise SystemExit", signum)
    raise SystemExit


def _parent_handler(signum, frame):
    """"Catch exit signal in parent process and forward it to children."""
    global children, logger
    logger.info("Caught signal %d, sending SIGTERM to children %s",
                signum, children)
    [os.kill(pid, SIGTERM) for pid in children]


def child(cmdline):
    """The context of the child process"""

    # Cmd line argument parsing
    (opts, args) = parse_arguments(cmdline)
    disp = Dispatcher(debug=opts.debug)

    # Start the event loop
    disp.wait()


def parse_arguments(args):
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-d", "--debug", action="store_true", default=False,
                      dest="debug", help="Enable debug mode")
    parser.add_option("-w", "--workers", default=2, dest="workers",
                      help="Number of workers to spawn", type="int")
    parser.add_option("-p", '--pid-file', dest="pid_file",
                      default=os.path.join(os.getcwd(), "dispatcher.pid"),
                      help="Save PID to file (default:%s)" %
                           os.path.join(os.getcwd(), "dispatcher.pid"))
    parser.add_option("--purge-queues", action="store_true",
                      default=False, dest="purge_queues",
                      help="Remove all declared queues (DANGEROUS!)")
    parser.add_option("--purge-exchanges", action="store_true",
                      default=False, dest="purge_exchanges",
                      help="Remove all exchanges. Implies deleting all queues \
                           first (DANGEROUS!)")
    parser.add_option("--drain-queue", dest="drain_queue",
                      help="Strips a queue from all outstanding messages")

    return parser.parse_args(args)


def purge_queues():
    """
        Delete declared queues from RabbitMQ. Use with care!
    """
    global QUEUES, BINDINGS
    conn = get_connection()
    chan = conn.channel()

    print "Queues to be deleted: ", QUEUES

    if not get_user_confirmation():
        return

    for queue in QUEUES:
        try:
            chan.queue_delete(queue=queue)
            print "Deleting queue %s" % queue
        except amqp.exceptions.AMQPChannelException as e:
            print e.amqp_reply_code, " ", e.amqp_reply_text
            chan = conn.channel()

    chan.connection.close()


def purge_exchanges():
    """Delete declared exchanges from RabbitMQ, after removing all queues"""
    global QUEUES, BINDINGS
    purge_queues()

    conn = get_connection()
    chan = conn.channel()

    print "Exchanges to be deleted: ", settings.EXCHANGES

    if not get_user_confirmation():
        return

    for exchange in settings.EXCHANGES:
        try:
            chan.exchange_delete(exchange=exchange)
        except amqp.exceptions.AMQPChannelException as e:
            print e.amqp_reply_code, " ", e.amqp_reply_text

    chan.connection.close()


def drain_queue(queue):
    """Strip a (declared) queue from all outstanding messages"""
    global QUEUES, BINDINGS
    if not queue:
        return

    if not queue in QUEUES:
        print "Queue %s not configured" % queue
        return

    print "Queue to be drained: %s" % queue

    if not get_user_confirmation():
        return
    conn = get_connection()
    chan = conn.channel()

    # Register a temporary queue binding
    for binding in BINDINGS:
        if binding[0] == queue:
            exch = binding[1]

    if not exch:
        print "Queue not bound to any exchange: %s" % queue
        return

    chan.queue_bind(queue=queue, exchange=exch, routing_key='#')
    tag = chan.basic_consume(queue=queue, callback=callbacks.dummy_proc)

    print "Queue draining about to start, hit Ctrl+c when done"
    time.sleep(2)
    print "Queue draining starting"

    signal(SIGTERM, _exit_handler)
    signal(SIGINT, _exit_handler)

    num_processed = 0
    while True:
        chan.wait()
        num_processed += 1
        sys.stderr.write("Ignored %d messages\r" % num_processed)

    chan.basic_cancel(tag)
    chan.connection.close()


def get_connection():
    conn = amqp.Connection(host=settings.RABBIT_HOST,
                           userid=settings.RABBIT_USERNAME,
                           password=settings.RABBIT_PASSWORD,
                           virtual_host=settings.RABBIT_VHOST)
    return conn


def get_user_confirmation():
    ans = raw_input("Are you sure (N/y):")

    if not ans:
        return False
    if ans not in ['Y', 'y']:
        return False
    return True


def debug_mode():
    disp = Dispatcher(debug=True)
    signal(SIGINT, _exit_handler)
    signal(SIGTERM, _exit_handler)

    disp.wait()


def daemon_mode(opts):
    global children, logger

    # Create pidfile,
    # take care of differences between python-daemon versions
    try:
        pidf = pidfile.TimeoutPIDLockFile(opts.pid_file, 10)
    except:
        pidf = pidlockfile.TimeoutPIDLockFile(opts.pid_file, 10)

    pidf.acquire()

    logger.info("Became a daemon")

    # Fork workers
    children = []

    i = 0
    while i < opts.workers:
        newpid = os.fork()

        if newpid == 0:
            signal(SIGINT, _exit_handler)
            signal(SIGTERM, _exit_handler)
            child(sys.argv[1:])
            sys.exit(1)
        else:
            pids = (os.getpid(), newpid)
            logger.debug("%d, forked child: %d" % pids)
            children.append(pids[1])
        i += 1

    # Catch signals to ensure graceful shutdown
    signal(SIGINT, _parent_handler)
    signal(SIGTERM, _parent_handler)

    # Wait for all children processes to die, one by one
    try:
        for pid in children:
            try:
                os.waitpid(pid, 0)
            except Exception:
                pass
    finally:
        pidf.release()


def main():
    global logger
    (opts, args) = parse_arguments(sys.argv[1:])

    logger = log.get_logger("synnefo.dispatcher")

    # Init the global variables containing the queues
    _init_queues()

    # Special case for the clean up queues action
    if opts.purge_queues:
        purge_queues()
        return

    # Special case for the clean up exch action
    if opts.purge_exchanges:
        purge_exchanges()
        return

    if opts.drain_queue:
        drain_queue(opts.drain_queue)
        return

    # Debug mode, process messages without spawning workers
    if opts.debug:
        log.console_output(logger)
        debug_mode()
        return

    # Redirect stdout and stderr to the fileno of the first
    # file-based handler for this logger
    stdout_stderr_handler = None
    files_preserve = None
    for handler in logger.handlers:
        if hasattr(handler, 'stream') and hasattr(handler.stream, 'fileno'):
            stdout_stderr_handler = handler.stream
            files_preserve = [handler.stream]
            break

    daemon_context = daemon.DaemonContext(
        stdout=stdout_stderr_handler,
        stderr=stdout_stderr_handler,
        files_preserve=files_preserve,
        umask=022)

    daemon_context.open()

    # Catch every exception, make sure it gets logged properly
    try:
        daemon_mode(opts)
    except Exception:
        exc = "".join(traceback.format_exception(*sys.exc_info()))
        logger.critical(exc)
        raise


if __name__ == "__main__":
    sys.exit(main())

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
