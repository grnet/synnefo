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

# Callback functions used by the dispatcher to process incoming notifications
# from AMQP queues.

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

        if msg["operation"] == "OP_INSTANCE_QUERY_DATA":
            return status_job_finished(message)

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
    _logger.debug("Request to trigger status update: %s", message.body)

    try:
        msg = json.loads(message.body)

        if msg["type"] != "reconcile" :
             _logger.error("Message is of unknown type %s", msg["type"])
             return

        if msg["vmid"] == "" :
            _logger.error("Reconciliate message does not specify a VM id")
            return

        vm = VirtualMachine.objects.get(id=msg["vmid"])
        backend.request_status_update(vm)

        message.channel.basic_ack(message.delivery_tag)
    except KeyError as k:
        _logger.error("Malformed incoming JSON, missing attributes: %s", k)
    except Exception as e:
        _logger.error("Unexpected error:%s", e)

def status_job_finished (message) :
    try:
        msg = json.loads(message.body)

        if msg["operation"] != 'OP_INSTANCE_QUERY_DATA':
            _logger.error("Message is of unknown type %s", msg["operation"])
            return

        if msg["status"] != "success" :
            _logger.warn("Ignoring non-success status update from job %d on VM %s",
                          msg['jobId'], msg['instance'])
            return

        status = backend.get_job_status(msg['jobId'])

        _logger.debug("Node status job result: %s" % status)

        stat = json.loads(status)

        if stat["summary"] != "INSTANCE_QUERY_DATA" or \
           type(stat["opresult"]) is not list:
             _logger.error("Status is of unknown type %s", stat["summary"])
             return

        req_state = stat['opresult'][msg['instance']]['config_state']
        run_state = stat['opresult'][msg['instance']]['run_state']
        vm = VirtualMachine.objects.get(name=msg['instance'])
        backend.update_status(vm, run_state)
        
        message.channel.basic_ack(message.delivery_tag)
    except KeyError as k:
        _logger.error("Malformed incoming JSON, missing attributes: %s", k)
    except Exception as e:
        _logger.error("Unexpected error:%s"%e)

def dummy_proc(message):
    try:
        msg = json.loads(message.body)
        _logger.debug("Msg (exchange:%s) ", msg)
        message.channel.basic_ack(message.delivery_tag)
    except Exception as e:
        _logger.error("Could not receive message %s" % e.message)
        pass
