#!/usr/bin/env python
#
# Copyright (c) 2010 Greek Research and Technology Network
#
"""Receive Ganeti events over RabbitMQ, update VM state in DB.

This daemon receives job notifications from ganeti-amqpd
and updates VM state in the DB accordingly.

"""

from django.core.management import setup_environ

import sys
import os
path = os.path.normpath(os.path.join(os.getcwd(), '..'))
sys.path.append(path)
import synnefo.settings as settings

setup_environ(settings)

from amqplib import client_0_8 as amqp

import json
import logging
import traceback
import time
import socket

import daemon
from signal import signal, SIGINT, SIGTERM, SIGKILL

from synnefo.db.models import VirtualMachine
from synnefo.logic import utils, backend

class Dispatcher:

    logger = None
    chan = None
    debug = False
    clienttags = []

    def __init__(self, debug = False, logger = None):
        self.logger = logger
        self.debug = debug
        self._init()

    def update_db(self, message):
        try:
            msg = json.loads(message.body)

            if msg["type"] != "ganeti-op-status":
                self.logger.error("Message is of uknown type %s." % (msg["type"],))
                return

            vmid = utils.id_from_instance_name(msg["instance"])
            vm = VirtualMachine.objects.get(id=vmid)

            self.logger.debug("Processing msg: %s" % (msg,))
            backend.process_backend_msg(vm, msg["jobId"], msg["operation"], msg["status"], msg["logmsg"])
            self.logger.debug("Done processing msg for vm %s." % (msg["instance"]))

        except KeyError:
            self.logger.error("Malformed incoming JSON, missing attributes: " + message.body)
        except VirtualMachine.InvalidBackendIdError:
            self.logger.debug("Ignoring msg for unknown instance %s." % (msg["instance"],))
        except VirtualMachine.DoesNotExist:
            self.logger.error("VM for instance %s with id %d not found in DB." % (msg["instance"], vmid))
        except Exception as e:
            self.logger.error("Unexpected error:\n" + "".join(traceback.format_exception(*sys.exc_info())))
            return
        finally:
            message.channel.basic_ack(message.delivery_tag)

    def send_email(self, message):
        self.logger.debug("Request to send email message")
        message.channel.basic_ack(message.delivery_tag)

    def update_credits(self, message):
        self.logger.debug("Request to update credits")
        message.channel.basic_ack(message.delivery_tag)

    def dummy_proc(self, message):
        try:
            msg = json.loads(message.body)
            self.logger.debug("Msg to %s (%s) " % message.channel, msg)
        finally:
            message.channel.basic_ack(message.delivery_tag)

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

    def _init(self):
        self._open_channel()

        for exchange in settings.EXCHANGES:
            self.chan.exchange_declare(exchange=exchange, type="topic", durable=True, auto_delete=False)

        for queue in settings.QUEUES:
            self.chan.queue_declare(queue=queue, durable=True, exclusive=False, auto_delete=False)

        bindings = None

        if self.debug:
            #Special queue handling, should not appear in production
            self.chan.queue_declare(queue=settings.QUEUE_DEBUG, durable=True, exclusive=False, auto_delete=False)
            bindings = settings.BINDINGS_DEBUG
        else:
            bindings = settings.BINDINGS

        for binding in bindings:
            self.chan.queue_bind(queue=binding[0], exchange=binding[1], routing_key=binding[2])
            tag = self.chan.basic_consume(queue=binding[0], callback=binding[3])
            self.logger.debug("Binding %s on queue %s to %s" % (binding[2], binding[0], binding[3]))
            self.clienttags.append(tag)

    def _open_channel(self):
        conn = None
        while conn == None:
            self.logger.info("Attempting to connect to %s", settings.RABBIT_HOST)
            try:
                conn = amqp.Connection( host=settings.RABBIT_HOST,
                                    userid=settings.RABBIT_USERNAME,
                                    password=settings.RABBIT_PASSWORD,
                                    virtual_host=settings.RABBIT_VHOST)
            except socket.error:
                time.sleep(1)
                pass

        self.logger.info("Connection succesful, opening channel")
        self.chan = conn.channel()

def exit_handler(signum, frame):
    global handler_logger

    handler_logger.info("Caught fatal signal %d, will raise SystemExit", signum)
    raise SystemExit

def child(cmdline):
    #Cmd line argument parsing
    (opts, args) = parse_arguments(cmdline)

    # Initialize logger
    lvl = logging.DEBUG if opts.debug else logging.INFO
    logger = logging.getLogger("okeanos.dispatcher")
    logger.setLevel(lvl)
    formatter = logging.Formatter("%(asctime)s %(module)s[%(process)d] %(levelname)s: %(message)s",
            "%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(opts.log_file)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    d = Dispatcher(debug = opts.debug, logger = logger)

    d.wait()

def parse_arguments(args):
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-d", "--debug", action="store_false", default=False, dest="debug",
            help="Enable debug mode")
    parser.add_option("-l", "--log", dest="log_file",
            default=settings.DISPATCHER_LOG_FILE,
            metavar="FILE",
            help="Write log to FILE instead of %s" %
            settings.DISPATCHER_LOG_FILE)
    parser.add_option("-c", "--cleanup-queues", action="store_true", default=False, dest="cleanup_queues",
            help="Remove from RabbitMQ all queues declared in settings.py (DANGEROUS!)")
    
    return parser.parse_args(args)

def cleanup_queues() :

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

    for exchange in settings.EXCHANGES:
        try:
            chan.exchange_delete(exchange=exchange)
        except amqp.exceptions.AMQPChannelException as e:
            print e.amqp_reply_code, " ", e.amqp_reply_text

    for queue in settings.QUEUES:
        try:
            chan.queue_delete(queue=queue)
        except amqp.exceptions.AMQPChannelException as e:
            print e.amqp_reply_code, " ", e.amqp_reply_text

def main():
    global logger
    (opts, args) = parse_arguments(sys.argv[1:])

    if opts.cleanup_queues:
        cleanup_queues()
        return

    #newpid = os.fork()
    #if newpid == 0:
    child(sys.argv[1:])
    #else:
    #    pids = (os.getpid(), newpid)
    #    print "parent: %d, child: %d" % pids

    # Become a daemon:
    # Redirect stdout and stderr to handler.stream to catch
    # early errors in the daemonization process [e.g., pidfile creation]
    # which will otherwise go to /dev/null.
    #daemon_context = daemon.DaemonContext(
    #        umask=022,
    #        stdout=handler.stream,
    #        stderr=handler.stream,
    #        files_preserve=[handler.stream])
    #daemon_context.open()
    #logger.info("Became a daemon")
    
    # Catch signals to ensure graceful shutdown
    #signal(SIGINT, exit_handler)
    #signal(SIGTERM, exit_handler)
    #signal(SIGKILL, exit_handler)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
