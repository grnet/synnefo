#
# Callback functions used by the dispatcher
# to process incoming notifications from AMQP queues.
#
# Copyright 2010 Greek Research and Technology Network
#
import traceback
import json
import logging
import sys

from synnefo.db.models import VirtualMachine
from synnefo.logic import utils, backend, email_send

_logger = logging.getLogger("synnefo.dispatcher")

def update_db(message):
    """Process the status of a VM based on a ganeti status message"""
    _logger.debug("Processing ganeti-op-status msg: %s", message.body)
    try:
        msg = json.loads(message.body)

        if msg["type"] != "ganeti-op-status":
            _logger.error("Message is of unknown type %s.", msg["type"])
            return

        vmid = utils.id_from_instance_name(msg["instance"])
        vm = VirtualMachine.objects.get(id=vmid)

        backend.process_op_status(vm, msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        _logger.debug("Done processing ganeti-op-status msg for vm %s.",
                      msg["instance"])
        message.channel.basic_ack(message.delivery_tag)
    except KeyError:
        _logger.error("Malformed incoming JSON, missing attributes: %s",
                      message.body)
    except VirtualMachine.InvalidBackendIdError:
        _logger.debug("Ignoring msg for unknown instance %s.",
                      msg["instance"])
    except VirtualMachine.DoesNotExist:
        _logger.error("VM for instance %s with id %d not found in DB.",
                      msg["instance"], vmid)
    except Exception as e:
        _logger.error("Unexpected error:\n%s" %
            "".join(traceback.format_exception(*sys.exc_info())))


def update_net(message):
    """Process a network status update notification from Ganeti"""
    _logger.debug("Processing ganeti-net-status msg: %s", message.body)
    try:
        msg = json.loads(message.body)

        if msg["type"] != "ganeti-net-status":
            _logger.error("Message is of unknown type %s", msg["type"])
            return

        vmid = utils.id_from_instance_name(msg["instance"])
        vm = VirtualMachine.objects.get(id=vmid)

        backend.process_net_status(vm, msg["nics"])
        _logger.debug("Done processing ganeti-net-status msg for vm %s.",
                      msg["instance"])
        message.channel.basic_ack(message.delivery_tag)
    except KeyError:
        _logger.error("Malformed incoming JSON, missing attributes: %s",
                      message.body)
    except VirtualMachine.InvalidBackendIdError:
        _logger.debug("Ignoring msg for unknown instance %s.",
                      msg["instance"])
    except VirtualMachine.DoesNotExist:
        _logger.error("VM for instance %s with id %d not found in DB.",
                      msg["instance"], vmid)
    except Exception as e:
        _logger.error("Unexpected error:\n%s" %
            "".join(traceback.format_exception(*sys.exc_info())))


def send_email(message):
    """Process an email submission request"""

    try:
        msg = json.loads(message.body)

        email_send.send(frm=msg['frm'], to = msg['to'],
                        body=msg['body'], subject=msg['subject'])
        message.channel.basic_ack(message.delivery_tag)
    except KeyError:
        _logger.error("Malformed incoming JSON, missing attributes: %s",
                      message.body)
    except Exception as e:
        _logger.error("Unexpected error:%s\n%s",
                      (e.message,"".
                      join(traceback.format_exception(*sys.exc_info()))))


def update_credits(message):
    _logger.debug("Request to update credits")
    message.channel.basic_ack(message.delivery_tag)


def dummy_proc(message):
    try:
        msg = json.loads(message.body)
        _logger.debug("Msg (exchange:%s) ", msg)
        message.channel.basic_ack(message.delivery_tag)
    except Exception as e:
        _logger.error("Could not receive message %s" % e.message)
        pass
