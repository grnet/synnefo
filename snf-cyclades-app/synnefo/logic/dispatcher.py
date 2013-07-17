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

# Fix path to import synnefo settings
import sys
import os
path = os.path.normpath(os.path.join(os.getcwd(), '..'))
sys.path.append(path)
from django.conf import settings
setup_environ(settings)

from django.db import close_connection

import time

import daemon
import daemon.runner
from lockfile import LockTimeout
# Take care of differences between python-daemon versions.
try:
    from daemon import pidfile as pidlockfile
except:
    from daemon import pidlockfile
import setproctitle

from synnefo.lib.amqp import AMQPClient
from synnefo.logic import callbacks
from synnefo.logic import queues

import logging

log = logging.getLogger("dispatcher")
log_amqp = logging.getLogger("amqp")
log_logic = logging.getLogger("synnefo.logic")

LOGGERS = [log, log_amqp, log_logic]


class Dispatcher:
    debug = False

    def __init__(self, debug=False):
        self.debug = debug
        self._init()

    def wait(self):
        log.info("Waiting for messages..")
        timeout = 600
        while True:
            try:
                # Close the Django DB connection before processing
                # every incoming message. This plays nicely with
                # DB connection pooling, if enabled and allows
                # the dispatcher to recover from broken connections
                # gracefully.
                close_connection()
                msg = self.client.basic_wait(timeout=timeout)
                if not msg:
                    log.warning("Idle connection for %d seconds. Will connect"
                                " to a different host. Verify that"
                                " snf-ganeti-eventd is running!!", timeout)
                    self.client.reconnect()
            except SystemExit:
                break
            except Exception as e:
                log.exception("Caught unexpected exception: %s", e)

        self.client.basic_cancel()
        self.client.close()

    def _init(self):
        log.info("Initializing")

        self.client = AMQPClient(logger=log_amqp)
        # Connect to AMQP host
        self.client.connect()

        # Declare queues and exchanges
        exchange = settings.EXCHANGE_GANETI
        exchange_dl = queues.convert_exchange_to_dead(exchange)
        self.client.exchange_declare(exchange=exchange,
                                     type="topic")
        self.client.exchange_declare(exchange=exchange_dl,
                                     type="topic")

        for queue in queues.QUEUES:
            # Queues are mirrored to all RabbitMQ brokers
            self.client.queue_declare(queue=queue, mirrored=True,
                                      dead_letter_exchange=exchange_dl)
            # Declare the corresponding dead-letter queue
            queue_dl = queues.convert_queue_to_dead(queue)
            self.client.queue_declare(queue=queue_dl, mirrored=True)

        # Bind queues to handler methods
        for binding in queues.BINDINGS:
            try:
                callback = getattr(callbacks, binding[3])
            except AttributeError:
                log.error("Cannot find callback %s", binding[3])
                raise SystemExit(1)
            queue = binding[0]
            exchange = binding[1]
            routing_key = binding[2]

            self.client.queue_bind(queue=queue, exchange=exchange,
                                   routing_key=routing_key)

            self.client.basic_consume(queue=binding[0],
                                      callback=callback,
                                      prefetch_count=5)

            queue_dl = queues.convert_queue_to_dead(queue)
            exchange_dl = queues.convert_exchange_to_dead(exchange)
            # Bind the corresponding dead-letter queue
            self.client.queue_bind(queue=queue_dl,
                                   exchange=exchange_dl,
                                   routing_key=routing_key)

            log.debug("Binding %s(%s) to queue %s with handler %s",
                      exchange, routing_key, queue, binding[3])


def parse_arguments(args):
    from optparse import OptionParser

    default_pid_file = \
        os.path.join(".", "var", "run", "synnefo", "dispatcher.pid")[1:]
    parser = OptionParser()
    parser.add_option("-d", "--debug", action="store_true", default=False,
                      dest="debug", help="Enable debug mode")
    parser.add_option("-w", "--workers", default=2, dest="workers",
                      help="Number of workers to spawn", type="int")
    parser.add_option("-p", "--pid-file", dest="pid_file",
                      default=default_pid_file,
                      help="Save PID to file (default: %s)" % default_pid_file)
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
    client = AMQPClient(max_retries=120)
    client.connect()

    print "Queues to be deleted: ", queues.QUEUES

    if not get_user_confirmation():
        return

    for queue in queues.QUEUES:
        result = client.queue_delete(queue=queue)
        print "Deleting queue %s. Result: %s" % (queue, result)

    client.close()


def purge_exchanges():
    """Delete declared exchanges from RabbitMQ, after removing all queues"""
    purge_queues()

    client = AMQPClient()
    client.connect()

    exchanges = queues.EXCHANGES
    print "Exchanges to be deleted: ", exchanges

    if not get_user_confirmation():
        return

    for exch in exchanges:
        result = client.exchange_delete(exchange=exch)
        print "Deleting exchange %s. Result: %s" % (exch, result)
    client.close()


def drain_queue(queue):
    """Strip a (declared) queue from all outstanding messages"""
    if not queue:
        return

    if not queue in queues.QUEUES:
        print "Queue %s not configured" % queue
        return

    print "Queue to be drained: %s" % queue

    if not get_user_confirmation():
        return

    client = AMQPClient()
    client.connect()

    tag = client.basic_consume(queue=queue, callback=callbacks.dummy_proc)

    print "Queue draining about to start, hit Ctrl+c when done"
    time.sleep(2)
    print "Queue draining starting"

    num_processed = 0
    while True:
        client.basic_wait()
        num_processed += 1
        sys.stderr.write("Ignored %d messages\r" % num_processed)

    client.basic_cancel(tag)
    client.close()


def get_user_confirmation():
    ans = raw_input("Are you sure (N/y):")

    if not ans:
        return False
    if ans not in ['Y', 'y']:
        return False
    return True


def debug_mode():
    disp = Dispatcher(debug=True)
    disp.wait()


def daemon_mode(opts):
    disp = Dispatcher(debug=False)
    disp.wait()


def setup_logging(opts):
    import logging
    formatter = logging.Formatter("%(asctime)s %(name)s %(module)s"
                                  " [%(levelname)s] %(message)s")
    if opts.debug:
        log_handler = logging.StreamHandler()
        log_handler.setFormatter(formatter)
    else:
        import logging.handlers
        log_file = "/var/log/synnefo/dispatcher.log"
        log_handler = logging.handlers.WatchedFileHandler(log_file)
        log_handler.setFormatter(formatter)

    for l in LOGGERS:
        l.addHandler(log_handler)
        l.setLevel(logging.DEBUG)


def main():
    (opts, args) = parse_arguments(sys.argv[1:])

    # Rename this process so 'ps' output looks like this is a native
    # executable.  Can not seperate command-line arguments from actual name of
    # the executable by NUL bytes, so only show the name of the executable
    # instead.  setproctitle.setproctitle("\x00".join(sys.argv))
    setproctitle.setproctitle(sys.argv[0])
    setup_logging(opts)

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

    # Debug mode, process messages without daemonizing
    if opts.debug:
        debug_mode()
        return

    # Create pidfile,
    pidf = pidlockfile.TimeoutPIDLockFile(opts.pid_file, 10)

    if daemon.runner.is_pidfile_stale(pidf):
        log.warning("Removing stale PID lock file %s", pidf.path)
        pidf.break_lock()

    files_preserve = []
    for handler in log.handlers:
        stream = getattr(handler, 'stream')
        if stream and hasattr(stream, 'fileno'):
            files_preserve.append(handler.stream)

    stderr_stream = None
    for handler in log.handlers:
        stream = getattr(handler, 'stream')
        if stream and hasattr(handler, 'baseFilename'):
            stderr_stream = stream
            break

    daemon_context = daemon.DaemonContext(
        pidfile=pidf,
        umask=0022,
        stdout=stderr_stream,
        stderr=stderr_stream,
        files_preserve=files_preserve)

    try:
        daemon_context.open()
    except (pidlockfile.AlreadyLocked, LockTimeout):
        log.critical("Failed to lock pidfile %s, another instance running?",
                     pidf.path)
        sys.exit(1)

    log.info("Became a daemon")

    if 'gevent' in sys.modules:
        # A fork() has occured while daemonizing. If running in
        # gevent context we *must* reinit gevent
        log.debug("gevent imported. Reinitializing gevent")
        import gevent
        gevent.reinit()

    # Catch every exception, make sure it gets logged properly
    try:
        daemon_mode(opts)
    except Exception:
        log.exception("Unknown error")
        raise

if __name__ == "__main__":
    sys.exit(main())

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
