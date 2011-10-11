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

import logging
import socket
import traceback
import json
import sys

from synnefo.db.models import VirtualMachine
from synnefo.logic import utils, backend, email_send


log = logging.getLogger()


def update_db(message):
    """Process a notification of type 'ganeti-op-status'"""
    log.debug("Processing ganeti-op-status msg: %s", message.body)
    msg = None
    try:
        msg = json.loads(message.body)

        if msg["type"] != "ganeti-op-status":
            log.error("Message is of unknown type %s.", msg["type"])
            return

        if msg["operation"] == "OP_INSTANCE_QUERY_DATA":
            return status_job_finished(message)

        vmid = utils.id_from_instance_name(msg["instance"])
        vm = VirtualMachine.objects.get(id=vmid)

        backend.process_op_status(vm, msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        log.debug("Done processing ganeti-op-status msg for vm %s.",
                      msg["instance"])
        message.channel.basic_ack(message.delivery_tag)
    except KeyError:
        log.error("Malformed incoming JSON, missing attributes: %s",
                      message.body)
    except VirtualMachine.InvalidBackendIdError:
        log.debug("Ignoring msg for unknown instance %s.", msg["instance"])
    except VirtualMachine.InvalidBackendMsgError, e:
        log.debug("Ignoring msg of unknown type: %s.", e)
    except VirtualMachine.DoesNotExist:
        log.error("VM for instance %s with id %d not found in DB.",
                      msg["instance"], vmid)
    except Exception as e:
        log.exception("Unexpected error, msg: %s", msg)


def update_net(message):
    """Process a notification of type 'ganeti-net-status'"""
    log.debug("Processing ganeti-net-status msg: %s", message.body)
    msg = None
    try:
        msg = json.loads(message.body)

        if msg["type"] != "ganeti-net-status":
            log.error("Message is of unknown type %s", msg["type"])
            return

        vmid = utils.id_from_instance_name(msg["instance"])
        vm = VirtualMachine.objects.get(id=vmid)

        backend.process_net_status(vm, msg["nics"])
        log.debug("Done processing ganeti-net-status msg for vm %s.",
                      msg["instance"])
        message.channel.basic_ack(message.delivery_tag)
    except KeyError:
        log.error("Malformed incoming JSON, missing attributes: %s",
                      message.body)
    except VirtualMachine.InvalidBackendIdError:
        log.debug("Ignoring msg for unknown instance %s.", msg["instance"])
    except VirtualMachine.DoesNotExist:
        log.error("VM for instance %s with id %d not found in DB.",
                      msg["instance"], vmid)
    except Exception as e:
        log.exception("Unexpected error, msg: %s", msg)


def send_email(message):
    """Process an email submission request"""
    msg = None
    try:
        msg = json.loads(message.body)

        sent = email_send.send(sender=msg['frm'], recipient = msg['to'],
                        body=msg['body'], subject=msg['subject'])

        if not sent:
            log.warn("Failed to send email to %s", msg['to'])
        else:
            message.channel.basic_ack(message.delivery_tag)
    except KeyError:
        log.error("Malformed incoming JSON, missing attributes: %s",
                      message.body)
    except socket.error as e:
        log.error("Cannot connect to SMTP server:%s\n", e)
    except Exception as e:
        log.exception("Unexpected error, msg: %s", msg)
        raise


def update_credits(message):
    log.debug("Request to update credits")
    message.channel.basic_ack(message.delivery_tag)


def update_build_progress(message):
    """Process a create progress message"""
    log.debug("Processing ganeti-create-progress msg: %s", message.body)
    msg = None
    try:
        msg = json.loads(message.body)

        if msg['type'] != "ganeti-create-progress":
            log.error("Message is of unknown type %s", msg["type"])
            return

        # XXX: The following assumes names like snf-12
        vmid = msg['instance'].split('-')[1]
        vm = VirtualMachine.objects.get(id=vmid)

        backend.process_create_progress(vm, msg['rprogress'], None)
        log.debug("Done processing ganeti-create-progress msg for vm %s.",
                      msg["instance"])
        message.channel.basic_ack(message.delivery_tag)
    except KeyError:
        log.error("Malformed incoming JSON, missing attributes: %s",
                      message.body)
    except Exception as e:
        log.exception("Unexpected error, msg: %s", msg)
        raise


def trigger_status_update(message):
    """Triggers a status update job for a specific VM id"""
    log.debug("Request to trigger status update: %s", message.body)
    msg = None
    try:
        msg = json.loads(message.body)

        if msg["type"] != "reconcile":
             log.error("Message is of unknown type %s", msg["type"])
             return

        if msg["vmid"] == "":
            log.error("Reconciliation message does not specify a VM id")
            return

        vm = VirtualMachine.objects.get(id=msg["vmid"])
        backend.request_status_update(vm)

        message.channel.basic_ack(message.delivery_tag)
    except KeyError as k:
        log.error("Malformed incoming JSON, missing attributes: %s", k)
    except Exception as e:
        log.exception("Unexpected error, msg: %s", msg)


def status_job_finished(message):
    """Updates VM status based on a previously sent status update request"""
    msg = None
    try:
        msg = json.loads(message.body)

        if msg["operation"] != 'OP_INSTANCE_QUERY_DATA':
            log.error("Message is of unknown type %s", msg["operation"])
            return

        if msg["status"] != "success":
            log.warn("Ignoring non-success status update from job %d on VM %s",
                          msg['jobId'], msg['instance'])
            message.channel.basic_ack(message.delivery_tag)
            return

        status = backend.get_job_status(msg['jobId'])

        log.debug("Node status job result: %s", status)

        if status['summary'][0] != u'INSTANCE_QUERY_DATA':
             log.error("Status update is of unknown type %s",
                        status['summary'])
             return

        conf_state = status['opresult'][0][msg['instance']]['config_state']
        run_state = status['opresult'][0][msg['instance']]['run_state']

        # XXX: The following assumes names like snf-12
        instid = msg['instance'].split('-')[1]

        vm = VirtualMachine.objects.get(id = instid)

        if run_state == "up":
            opcode = "OP_INSTANCE_REBOOT"
        else:
            opcode = "OP_INSTANCE_SHUTDOWN"

        backend.process_op_status(vm=vm, jobid=msg['jobId'],opcode=opcode,
                                  status="success",
                                  logmsg="Reconciliation: simulated event")

        message.channel.basic_ack(message.delivery_tag)
    except KeyError as k:
        log.error("Malformed incoming JSON, missing attributes: %s", k)
    except Exception as e:
        log.exception("Unexpected error, msg: %s", msg)


def dummy_proc(message):
    try:
        log.debug("Msg: %s", message.body)
        message.channel.basic_ack(message.delivery_tag)
    except Exception as e:
        log.exception("Could not receive message")
        pass
