#!/usr/bin/env python
# Copyright (C) 2010-2015 GRNET S.A. and individual contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


""" Message queue setup, dispatch and admin

This program sets up connections to the queues configured in settings.py
and implements the message wait and dispatch loops. Actual messages are
handled in the dispatched functions.

"""

# Fix path to import synnefo settings
import sys
import os
path = os.path.normpath(os.path.join(os.getcwd(), '..'))
sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'
from django.conf import settings

from django.db import close_connection

import time

import json
import socket
import traceback
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
from synnefo.db.models import Backend, pooled_rapi_client

import logging
import select
import errno

log = logging.getLogger("dispatcher")
log_amqp = logging.getLogger("amqp")
log_logic = logging.getLogger("synnefo.logic")

LOGGERS = [log, log_amqp, log_logic]

# Seconds for which snf-dispatcher will wait on a queue with no messages.
# After this timeout the snf-dispatcher will reconnect to the AMQP broker.
DISPATCHER_RECONNECT_TIMEOUT = 600


# Time out after S Seconds while waiting messages from Ganeti clusters to
# arrive. Warning: During this period snf-dispatcher will not consume any other
# messages.
HEARTBEAT_TIMEOUT = 5
# Seconds that the heartbeat queue will exist while there are no consumers.
HEARTBEAT_QUEUE_TTL = 120
# Time out after S seconds while waiting acknowledgment from snf-dispatcher
# that the status check has started.
CHECK_TOOL_ACK_TIMEOUT = 10
# Time out after S seconds while waiting for the status report from
# snf-dispatcher to arrive.
CHECK_TOOL_REPORT_TIMEOUT = 30
# Seconds that the request queue will exist while there are no consumers.
REQUEST_QUEUE_TTL = 600


def get_hostname():
    return socket.gethostbyaddr(socket.gethostname())[0]


class Dispatcher:
    debug = False

    def __init__(self, debug=False):
        self.debug = debug
        self._init()

    def wait(self):
        log.info("Waiting for messages..")
        timeout = DISPATCHER_RECONNECT_TIMEOUT
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
                    self.client.reconnect(timeout=1)
            except select.error as e:
                if e[0] != errno.EINTR:
                    log.exception("Caught unexpected exception: %s", e)
                else:
                    break
            except (SystemExit, KeyboardInterrupt):
                break
            except Exception as e:
                log.exception("Caught unexpected exception: %s", e)

        log.info("Clean up AMQP connection before exit")
        self.client.basic_cancel(timeout=1)
        self.client.close(timeout=1)

    def _init(self):
        log.info("Initializing")

        # Set confirm buffer to 1 for heartbeat messages
        self.client = AMQPClient(logger=log_amqp, confirm_buffer=1)
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

        # Declare the queue that will be used for receiving requests, e.g. a
        # status check request
        hostname, pid = get_hostname(), os.getpid()
        queue = queues.get_dispatcher_request_queue(hostname, pid)
        self.client.queue_declare(queue=queue, mirrored=True,
                                  ttl=REQUEST_QUEUE_TTL)
        self.client.basic_consume(queue=queue, callback=handle_request)
        log.debug("Binding %s(%s) to queue %s with handler 'hadle_request'",
                  exchange, routing_key, queue)


def handle_request(client, msg):
    """Callback function for handling requests.

    Currently only 'status-check' action is supported.

    """

    client.basic_ack(msg)
    log.debug("Received request message: %s", msg)
    body = json.loads(msg["body"])
    reply_to = None
    try:
        reply_to = body["reply_to"]
        reply_to = reply_to.encode("utf-8")
        action = body["action"]
        assert(action == "status-check")
    except (KeyError, AssertionError) as e:
        log.warning("Invalid request message: %s. Error: %s", msg, e)
        if reply_to is not None:
            msg = {"status": "failed",
                   "reason": "Invalid request"}
            client.basic_publish("", reply_to, json.dumps(msg))
        return

    msg = {"action": action, "status": "started"}
    client.basic_publish("", reply_to, json.dumps(msg))

    # Declare 'heartbeat' queue and bind it to the exchange. The queue is
    # declared with a 'ttl' option in order to be automatically deleted.
    hostname, pid = get_hostname(), os.getpid()
    queue = queues.get_dispatcher_heartbeat_queue(hostname, pid)
    exchange = settings.EXCHANGE_GANETI
    routing_key = queues.EVENTD_HEARTBEAT_ROUTING_KEY
    client.queue_declare(queue=queue, mirrored=False, ttl=HEARTBEAT_QUEUE_TTL)
    client.queue_bind(queue=queue, exchange=exchange,
                      routing_key=routing_key)
    log.debug("Binding %s(%s) to queue %s", exchange, routing_key, queue)

    backends = Backend.objects.filter(offline=False)
    status = {}

    _OK = "ok"
    _FAIL = "fail"
    # Add cluster tag to trigger snf-ganeti-eventd
    tag = "snf:eventd:heartbeat:%s:%s" % (hostname, pid)
    for backend in backends:
        cluster = backend.clustername
        status[cluster] = {"RAPI": _FAIL, "eventd": _FAIL}
        try:
            with pooled_rapi_client(backend) as rapi:
                rapi.AddClusterTags(tags=[tag], dry_run=True)
        except:
            log.exception("Failed to send job to Ganeti cluster '%s' during"
                          " status check" % cluster)
            continue
        status[cluster]["RAPI"] = _OK

    start = time.time()
    while time.time() - start <= HEARTBEAT_TIMEOUT:
        msg = client.basic_get(queue, no_ack=True)
        if msg is None:
            time.sleep(0.1)
            continue
        log.debug("Received heartbeat msg: %s", msg)
        try:
            body = json.loads(msg["body"])
            cluster = body["cluster"]
            status[cluster]["eventd"] = _OK
        except:
            log.error("Received invalid heartbat msg: %s", msg)
        if not filter(lambda x: x["eventd"] == _FAIL, status.values()):
            break

    # Send back status report
    client.basic_publish("", reply_to, json.dumps({"status": status}))


def parse_arguments(args):
    from optparse import OptionParser

    default_pid_file = "/var/run/synnefo/snf-dispatcher.pid"
    description = ("The Synnefo Dispatcher Daemon consumes messages from an"
                   " AMQP broker and properly updates the Cyclades DB. These"
                   " messages are mostly asynchronous notifications about the"
                   " progress of jobs in the Ganeti backends.")
    parser = OptionParser(description=description)
    parser.add_option("-d", "--debug", action="store_true",
                      default=False, dest="debug",
                      help="Enable debug mode (do not turn into deamon)")
    parser.add_option("-p", "--pid-file", dest="pid_file",
                      default=default_pid_file,
                      help=("Location of PID file (default: %s)"
                            % default_pid_file))
    parser.add_option("--purge-queues", action="store_true",
                      default=False, dest="purge_queues",
                      help="Remove all queues (DANGEROUS!)")
    parser.add_option("--purge-exchanges", action="store_true",
                      default=False, dest="purge_exchanges",
                      help=("Remove all exchanges. Implies deleting all queues"
                            " first (DANGEROUS!)"))
    parser.add_option("--drain-queue", dest="drain_queue",
                      help="Drain a queue from all outstanding messages")
    parser.add_option("--status-check", dest="status_check",
                      default=False, action="store_true",
                      help="Trigger a status check for a running"
                           " snf-dispatcher process, that will check"
                           " communication between snf-dispatcher and Ganeti"
                           " backends via AMQP brokers")

    return parser.parse_args(args)


def check_dispatcher_status(pid_file):
    """Check the status of a running snf-dispatcher process.

    Check the status of a running snf-dispatcher process, the PID of which is
    contained in the 'pid_file'. This function will send a 'status-check'
    message to the running snf-dispatcher, wait for dispatcher's response and
    pretty-print the results.

    """
    dispatcher_pid = pidlockfile.read_pid_from_pidfile(pid_file)
    if dispatcher_pid is None:
        sys.stdout.write("snf-dispatcher with PID file '%s' is not running."
                         " PID file does not exist\n" % pid_file)
        sys.exit(1)
    sys.stdout.write("snf-dispatcher (PID: %s): running\n" % dispatcher_pid)

    hostname = get_hostname()
    local_queue = "snf:check_tool:%s:%s" % (hostname, os.getpid())
    dispatcher_queue = queues.get_dispatcher_request_queue(hostname,
                                                           dispatcher_pid)

    log_amqp.setLevel(logging.WARNING)
    try:
        client = AMQPClient(logger=log_amqp)
        client.connect()
        client.queue_declare(queue=local_queue, mirrored=False, exclusive=True)
        client.basic_consume(queue=local_queue, callback=lambda x, y: 0,
                             no_ack=True)
        msg = json.dumps({"action": "status-check", "reply_to": local_queue})
        client.basic_publish("", dispatcher_queue, msg)
    except:
        sys.stdout.write("Error while connecting with AMQP\nError:\n")
        traceback.print_exc()
        sys.exit(1)

    sys.stdout.write("AMQP -> snf-dispatcher: ")
    msg = client.basic_wait(timeout=CHECK_TOOL_ACK_TIMEOUT)
    if msg is None:
        sys.stdout.write("fail\n")
        sys.stdout.write("ERROR: No reply from snf-dipatcher after '%s'"
                         " seconds.\n" % CHECK_TOOL_ACK_TIMEOUT)
        sys.exit(1)
    else:
        try:
            body = json.loads(msg["body"])
            assert(body["action"] == "status-check"), "Invalid action"
            assert(body["status"] == "started"), "Invalid status"
            sys.stdout.write("ok\n")
        except Exception as e:
            sys.stdout.write("Received invalid msg from snf-dispatcher:"
                             " msg: %s error: %s\n" % (msg, e))
            sys.exit(1)

    msg = client.basic_wait(timeout=CHECK_TOOL_REPORT_TIMEOUT)
    if msg is None:
        sys.stdout.write("fail\n")
        sys.stdout.write("ERROR: No status repot after '%s' seconds.\n"
                         % CHECK_TOOL_REPORT_TIMEOUT)
        sys.exit(1)

    sys.stdout.write("Backends:\n")
    status = json.loads(msg["body"])["status"]
    for backend, bstatus in sorted(status.items()):
        sys.stdout.write(" * %s: \n" % backend)
        sys.stdout.write("   snf-dispatcher -> ganeti: %s\n" %
                         bstatus["RAPI"])
        sys.stdout.write("   snf-ganeti-eventd -> AMQP: %s\n" %
                         bstatus["eventd"])
    sys.exit(0)


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
    if opts.debug or opts.status_check:
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
    # executable.  Cannot seperate command-line arguments from actual name of
    # the executable by NUL bytes, so only show the name of the executable
    # instead.  setproctitle.setproctitle("\x00".join(sys.argv))
    setproctitle.setproctitle(sys.argv[0])
    setup_logging(opts)

    if opts.status_check:
        check_dispatcher_status(opts.pid_file)
        return

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
