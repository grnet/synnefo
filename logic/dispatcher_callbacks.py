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
from synnefo.logic import utils, backend

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
    _logger.debug("Request to send email message")
    message.channel.basic_ack(message.delivery_tag)


def update_credits(message):
    _logger.debug("Request to update credits")
    message.channel.basic_ack(message.delivery_tag)

def trigger_status_update(message):
    _logger.debug("Request to trigger status update:", message.body)

    try:
        msg = json.loads(message.body)

        if msg["type"] != "reconciliate" :
             _logger.error("Message is of unknown type %s", msg["type"])
             return

        if msg["vm-id"] == "" :
            _logger.error("Message does not specify a VM id")
            return

        vm = VirtualMachine.objects.get(id=msg["vm-id"])
        backend.request_status_update(vm)

        message.channel.basic_ack(message.delivery_tag)
    except KeyError:
        _logger.error("Malformed incoming JSON, missing attributes: %s",
                      message.body)
    except Exception as e:
        _logger.error("Unexpected error:\n%s" %
                      "".join(traceback.format_exception(*sys.exc_info())))

def status_job_finished (message) :
    _logger.debug("Job status message received:", message.body)
    try:

        msg = message.body;

        if msg['operation'] != u'OP_INSTANCE_QUERY_DATA':
            _logger.error("Message is of unknown type %s", msg["operation"])
            return

        if msg["status"] != "success" :
            _logger.error("Status job %d for %s did not finish properly",
                          msg['jobId'], msg['instance'])
            return

        status = backend.get_job_status(msg['jobid'])

        if status["summary"] != "INSTANCE_QUERY_DATA" or type(status["opresult"]) is not list:
             _logger.error("Status is of unknown type %s", msg["summary"])
             return

        req_state = status['opresult'][msg['instance']]['config_state']
        run_state = status['opresult'][msg['instance']]['run_state']
        vm = VirtualMachine.objects.get(name=msg['instance'])
        backend.update_status(vm, run_state)
        
        message.channel.basic_ack(message.delivery_tag)
    except KeyError:
        _logger.error("Malformed incoming JSON, missing attributes: %s",
                      message.body)
    except Exception as e:
        _logger.error("Unexpected error:\n%s" %
                      "".join(traceback.format_exception(*sys.exc_info())))

def dummy_proc(message):
    try:
        msg = json.loads(message.body)
        _logger.debug("Msg (exchange:%s) ", msg)
        message.channel.basic_ack(message.delivery_tag)
    except Exception as e:
        _logger.error("Could not receive message %s" % e.message)
        pass
