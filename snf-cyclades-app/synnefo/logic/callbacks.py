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
import json
from functools import wraps
from datetime import datetime

from synnefo.db.models import VirtualMachine
from synnefo.logic import utils, backend

from synnefo.lib.utils import merge_time


log = logging.getLogger()


def is_update_required(func):
    """
    Decorator for checking if an incoming message needs to update the db.

    The database will not be updated in the following cases:
    - The message has been redelivered and the action has already been
      completed. In this case the event_time will be equal with the one
      in the database.
    - The message describes a previous state in the ganeti, from the one that is
      described in the db. In this case the event_time will be smaller from the
      one in the database.

    This decorator is also acknowledging the messages to the AMQP broker.

    """
    @wraps(func)
    def wrapper(client, message, *args, **kwargs):
        log.debug("Checking if action is required for msg %s",  message)

        try:
            msg = json.loads(message['body'])

            event_time = merge_time(msg['event_time'])

            vm_id = utils.id_from_instance_name(msg["instance"])
            vm = VirtualMachine.objects.get(id=vm_id)

            db_time = vm.backendtime
            if event_time <= db_time:
                format_ = "%d/%m/%y %H:%M:%S:%f"
                log.debug("Ignoring message. event_timestamp: %s db_timestamp: %s",
                          event_time.strftime(format_),
                          db_time.strftime(format_))
                client.basic_ack(message)
                return

            # New message. Update the database!
            func(client, message)

        except ValueError:
            log.error("Incoming message not in JSON format: %s", message)
            client.basic_ack(message)
        except KeyError:
            log.error("Malformed incoming JSON, missing attributes: %s",
                      message)
            client.basic_ack(message)
        except VirtualMachine.InvalidBackendIdError:
            log.debug("Ignoring msg for unknown instance %s.", msg['instance'])
            client.basic_ack(message)
        except VirtualMachine.DoesNotExist:
            log.error("VM for instance %s with id %d not found in DB.",
                      msg['instance'], vm_id)
            client.basic_ack(message)
        except Exception as e:
            log.exception("Unexpected error: %s, msg: %s", e, msg)
        else:
            # Acknowledge the message
            client.basic_ack(message)

    return wrapper


@is_update_required
def update_db(client, message):
    """Process a notification of type 'ganeti-op-status'"""
    log.debug("Processing ganeti-op-status msg: %s", message['body'])

    msg = json.loads(message['body'])

    if msg['type'] != "ganeti-op-status":
        log.error("Message is of unknown type %s.", msg['type'])
        return

    if msg['operation'] == "OP_INSTANCE_QUERY_DATA":
        return status_job_finished(client, message)

    vm_id = utils.id_from_instance_name(msg['instance'])
    vm = VirtualMachine.objects.get(id=vm_id)

    event_time = merge_time(msg['event_time'])
    backend.process_op_status(vm, event_time, msg['jobId'], msg['operation'],
                              msg['status'], msg['logmsg'])

    log.debug("Done processing ganeti-op-status msg for vm %s.",
              msg['instance'])


@is_update_required
def update_net(client, message):
    """Process a notification of type 'ganeti-net-status'"""
    log.debug("Processing ganeti-net-status msg: %s", message['body'])

    msg = json.loads(message['body'])

    if msg['type'] != "ganeti-net-status":
        log.error("Message is of unknown type %s", msg['type'])
        return

    vm_id = utils.id_from_instance_name(msg['instance'])
    vm = VirtualMachine.objects.get(id=vm_id)

    event_time = merge_time(msg['event_time'])
    backend.process_net_status(vm, event_time, msg['nics'])

    log.debug("Done processing ganeti-net-status msg for vm %s.",
              msg["instance"])


@is_update_required
def update_build_progress(client, message):
    """Process a create progress message"""
    log.debug("Processing ganeti-create-progress msg: %s", message['body'])

    msg = json.loads(message['body'])

    if msg['type'] != "ganeti-create-progress":
        log.error("Message is of unknown type %s", msg['type'])
        return

    vm_id = utils.id_from_instance_name(msg['instance'])
    vm = VirtualMachine.objects.get(id=vm_id)

    event_time = merge_time(msg['event_time'])
    backend.process_create_progress(vm, event_time, msg['rprogress'], None)

    log.debug("Done processing ganeti-create-progress msg for vm %s.",
              msg['instance'])


def status_job_finished(client, message):
    """Updates VM status based on a previously sent status update request"""

    msg = json.loads(message['body'])

    if msg['operation'] != 'OP_INSTANCE_QUERY_DATA':
        log.error("Message is of unknown type %s", msg['operation'])
        return

    if msg['status'] != 'success':
        log.warn("Ignoring non-success status update from job %d on VM %s",
                 msg['jobId'], msg['instance'])
        client.basic_ack(message.delivery_tag)
        return

    status = backend.get_job_status(msg['jobId'])

    log.debug("Node status job result: %s", status)

    if status['summary'][0] != u'INSTANCE_QUERY_DATA':
         log.error("Status update is of unknown type %s",
                    status['summary'])
         return

    conf_state = status['opresult'][0][msg['instance']]['config_state']
    run_state = status['opresult'][0][msg['instance']]['run_state']

    vm_id = utils.id_from_instance_name(msg['instance'])
    vm = VirtualMachine.objects.get(id = vm_id)

    if run_state == "up":
        opcode = "OP_INSTANCE_REBOOT"
    else:
        opcode = "OP_INSTANCE_SHUTDOWN"

    event_time = merge_time(msg['event_time'])
    backend.process_op_status(vm=vm, etime=event_time,
                              jobid=msg['jobId'], opcode=opcode,
                              status='success',
                              logmsg="Reconciliation: simulated event")

@is_update_required
def dummy_proc(client, message):
    try:
        log.debug("Msg: %s", message['body'])
        pass
    except Exception as e:
        log.exception("Could not receive message")
