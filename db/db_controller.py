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

from synnefo.db.models import VirtualMachine
from synnefo.logic import utils, backend

def update_db(message):
    logging.debug("Received message from RabbitMQ")
    try:
        msg = json.loads(message.body)

        if msg["type"] != "ganeti-op-status":
            logging.debug("Ignoring message of uknown type %s." % (msg["type"],))
            return

        vmid = utils.id_from_instance_name(msg["instance"])
        vm = VirtualMachine.objects.get(id=vmid)

        logging.debug("Processing msg: %s" % (msg,))
        backend.process_backend_msg(vm, msg["jobId"], msg["operation"], msg["status"], msg["logmsg"])
        logging.debug("Done processing msg for vm %s." % (msg["instance"]))

    except KeyError:
        logging.error("Malformed incoming JSON, missing attributes: " + message_data)
    except VirtualMachine.InvalidBackendIdError:
        logging.debug("Ignoring msg for unknown instance %s." % (msg["instance"],))
    except VirtualMachine.DoesNotExist:
        logging.error("VM for instance %s with id %d not found in DB." % (msg["instance"], vmid))
    except Exception as e:
        logging.error("Unexpected error:\n" + "".join(traceback.format_exception(*sys.exc_info())))
        return
    finally:
        message.channel.basic_ack(message.delivery_tag)

def main():

    conn = amqp.Connection( host=settings.RABBIT_HOST,
                            userid=settings.RABBIT_USERNAME,
                            password=settings.RABBIT_PASSWORD,
                            virtual_host=settings.RABBIT_VHOST)
    chan = conn.channel()
    chan.queue_declare(queue="events", durable=True, exclusive=False, auto_delete=False)
    chan.exchange_declare(exchange="ganeti", type="direct", durable=True,
            auto_delete=False)
    chan.queue_bind(queue="events", exchange="ganeti", routing_key="eventd")
    chan.basic_consume(queue="events", callback=update_db, consumer_tag="dbupdater")

    while True:
        chan.wait()

    chan.basic_cancel("dbupdater")
    chan.close()
    conn.close()
#TODO: Implement proper shutdown of channel

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())

# vim: set ts=4 sts=4 sw=4 et ai :
