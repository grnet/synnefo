import traceback
import json
import logging
import sys

from synnefo.db.models import VirtualMachine
from synnefo.logic import utils, backend

_logger = logging.getLogger("synnefo.dispatcher")

def update_db(message):
    _logger.debug("Processing msg: %s" % message.body)
    try:
        msg = json.loads(message.body)

        if msg["type"] != "ganeti-op-status":
            _logger.error("Message is of uknown type %s." % (msg["type"],))
            return

        vmid = utils.id_from_instance_name(msg["instance"])
        vm = VirtualMachine.objects.get(id=vmid)

        backend.process_backend_msg(vm, msg["jobId"], msg["operation"], msg["status"], msg["logmsg"])
        _logger.debug("Done processing msg for vm %s." % (msg["instance"]))
        message.channel.basic_ack(message.delivery_tag)
    except KeyError:
        _logger.error("Malformed incoming JSON, missing attributes: " + message.body)
    except VirtualMachine.InvalidBackendIdError:
        _logger.debug("Ignoring msg for unknown instance %s." % (msg["instance"],))
        message.channel.basic_ack(message.delivery_tag)
    except VirtualMachine.DoesNotExist:
        _logger.error("VM for instance %s with id %d not found in DB." % (msg["instance"], vmid))
    except Exception as e:
        _logger.error("Unexpected error:\n" + "".join(traceback.format_exception(*sys.exc_info())))

def send_email(message):
    _logger.debug("Request to send email message")
    message.channel.basic_ack(message.delivery_tag)


def update_credits(message):
    _logger.debug("Request to update credits")
    message.channel.basic_ack(message.delivery_tag)


def dummy_proc(message):
    try:
        msg = json.loads(message.body)
        _logger.debug("Msg (exchange:%s) " % (msg, ))
        message.channel.basic_ack(message.delivery_tag)
    except Exception as e:
        _logger.error("Could not receive message %s" % e.message)
        pass
