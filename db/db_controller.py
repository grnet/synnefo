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

logger = None

def update_db(message):
    try:
        msg = json.loads(message.body)

        if msg["type"] != "ganeti-op-status":
            logging.error("Message is of uknown type %s." % (msg["type"],))
            return

        vmid = utils.id_from_instance_name(msg["instance"])
        vm = VirtualMachine.objects.get(id=vmid)

        logging.debug("Processing msg: %s" % (msg,))
        backend.process_backend_msg(vm, msg["jobId"], msg["operation"], msg["status"], msg["logmsg"])
        logging.debug("Done processing msg for vm %s." % (msg["instance"]))

    except KeyError:
        logging.error("Malformed incoming JSON, missing attributes: " + message.body)
    except VirtualMachine.InvalidBackendIdError:
        logging.debug("Ignoring msg for unknown instance %s." % (msg["instance"],))
    except VirtualMachine.DoesNotExist:
        logging.error("VM for instance %s with id %d not found in DB." % (msg["instance"], vmid))
    except Exception as e:
        logging.error("Unexpected error:\n" + "".join(traceback.format_exception(*sys.exc_info())))
        return
    finally:
        message.channel.basic_ack(message.delivery_tag)

def send_email(message):
    logger.debug("Request to send email message")
    message.channel.basic_ack(message.delivery_tag)

def update_credits(message):
    logger.debug("Request to update credits")
    message.channel.basic_ack(message.delivery_tag)

def declare_queues(chan):
    chan.exchange_declare(exchange=settings.EXCHANGE_GANETI, type="topic", durable=True, auto_delete=False)
    chan.exchange_declare(exchange=settings.EXCHANGE_CRON, type="topic", durable=True, auto_delete=False)
    chan.exchange_declare(exchange=settings.EXCHANGE_API, type="topic", durable=True, auto_delete=False)

    chan.queue_declare(queue=settings.QUEUE_GANETI_EVENTS, durable=True, exclusive=False, auto_delete=False)
    chan.queue_declare(queue=settings.QUEUE_CRON_CREDITS, durable=True, exclusive=False, auto_delete=False)
    chan.queue_declare(queue=settings.QUEUE_API_EMAIL, durable=True, exclusive=False, auto_delete=False)
    chan.queue_declare(queue=settings.QUEUE_CRON_EMAIL, durable=True, exclusive=False, auto_delete=False)

def init_devel():
    chan = open_channel()
    declare_queues(chan)
    chan.queue_bind(queue=settings.QUEUE_GANETI_EVENTS, exchange=settings.EXCHANGE_GANETI, routing_key="event.*")
    chan.basic_consume(queue="events", callback=update_db, consumer_tag="dbupdater")
    return chan

def init():
    chan = open_channel()
    declare_queues(chan)
    chan.queue_bind(queue=settings.QUEUE_GANETI_EVENTS, exchange=settings.EXCHANGE_GANETI, routing_key="event.*")
    chan.basic_consume(queue="events", callback=update_db, consumer_tag="dbupdater")
    return chan

def parse_arguments(args):
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-d", "--debug", action="store_true", dest="debug",
            help="Enable debug mode")
    parser.add_option("-l", "--log", dest="log_file",
            default=settings.DISPATCHER_LOG_FILE,
            metavar="FILE",
            help="Write log to FILE instead of %s" %
            settings.DISPATCHER_LOG_FILE)

    return parser.parse_args(args)

def exit_handler(signum, frame):
    global handler_logger

    handler_logger.info("Caught fatal signal %d, will raise SystemExit", signum)
    raise SystemExit

def init_queues(debug):
    chan = None
    if debug:
        chan = init_devel()
    else:
        chan = init()
    return chan

def open_channel():
    conn = None
    while conn == None:
        logger.info("Attempting to connect to %s", settings.RABBIT_HOST)
        try:
            conn = amqp.Connection( host=settings.RABBIT_HOST,
                                    userid=settings.RABBIT_USERNAME,
                                    password=settings.RABBIT_PASSWORD,
                                    virtual_host=settings.RABBIT_VHOST)
        except socket.error:
            time.sleep(1)
            pass

    logger.info("Connection succesful, opening channel")
    return conn.channel()

def main():
    global logger
    (opts, args) = parse_arguments(sys.argv[1:])

    # Initialize logger
    lvl = logging.DEBUG if opts.debug else logging.INFO
    logger = logging.getLogger("okeanos.dispatcher")
    logger.setLevel(lvl)
    formatter = logging.Formatter("%(asctime)s %(module)s[%(process)d] %(levelname)s: %(message)s",
            "%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(opts.log_file)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    #Init the queues
    chan = init_queues(opts.debug)

    # Become a daemon:
    # Redirect stdout and stderr to handler.stream to catch
    # early errors in the daemonization process [e.g., pidfile creation]
    # which will otherwise go to /dev/null.
    daemon_context = daemon.DaemonContext(
            umask=022,
            stdout=handler.stream,
            stderr=handler.stream,
            files_preserve=[handler.stream])
    daemon_context.open()
    logger.info("Became a daemon")
    
    # Catch signals to ensure graceful shutdown
    signal(SIGINT, exit_handler)
    signal(SIGTERM, exit_handler)
    signal(SIGKILL, exit_handler)

    while True:
        try:
            chan.wait()
        except SystemExit:
            break

    chan.basic_cancel("dbupdater")
    chan.close()
    chan.connection.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
