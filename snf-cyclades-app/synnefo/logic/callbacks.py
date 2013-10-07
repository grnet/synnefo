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

from django.db import transaction
from synnefo.db.models import Backend, VirtualMachine, Network, BackendNetwork
from synnefo.logic import utils, backend as backend_mod

from synnefo.lib.utils import merge_time

log = logging.getLogger(__name__)


def handle_message_delivery(func):
    """ Generic decorator for handling messages.

    This decorator is responsible for converting the message into json format,
    handling of common exceptions and acknowledment of message if needed.

    """
    @wraps(func)
    def wrapper(client, message, *args, **kwargs):
        try:
            msg = None
            msg = json.loads(message['body'])
            func(msg)
            client.basic_ack(message)
        except ValueError as e:
            log.error("Incoming message not in JSON format %s: %s", e, message)
            client.basic_nack(message)
        except KeyError as e:
            log.error("Malformed incoming JSON, missing attribute %s: %s",
                      e, message)
            client.basic_nack(message)
        except Exception as e:
            if msg:
                log.exception("Unexpected error: %s, msg: %s", e, msg)
            else:
                log.exception("Unexpected error: %s", e)
            client.basic_reject(message)

    return wrapper


def instance_from_msg(func):
    """ Decorator for getting the VirtualMachine object of the msg.

    """
    @handle_message_delivery
    @wraps(func)
    def wrapper(msg):
        try:
            vm_id = utils.id_from_instance_name(msg["instance"])
            vm = VirtualMachine.objects.select_for_update().get(id=vm_id)
            func(vm, msg)
        except VirtualMachine.InvalidBackendIdError:
            log.debug("Ignoring msg for unknown instance %s.", msg['instance'])
        except VirtualMachine.DoesNotExist:
            log.error("VM for instance %s with id %d not found in DB.",
                      msg['instance'], vm_id)
        except Network.InvalidBackendIdError, Network.DoesNotExist:
            log.error("Invalid message", msg)
    return wrapper


def network_from_msg(func):
    """ Decorator for getting the BackendNetwork object of the msg.

    """
    @handle_message_delivery
    @wraps(func)
    def wrapper(msg):
        try:
            network_id = utils.id_from_network_name(msg["network"])
            network = Network.objects.select_for_update().get(id=network_id)
            backend = Backend.objects.get(clustername=msg['cluster'])
            bnet, new = BackendNetwork.objects.get_or_create(network=network,
                                                             backend=backend)
            if new:
                log.info("Created missing BackendNetwork %s", bnet)
            func(bnet, msg)
        except Network.InvalidBackendIdError:
            log.debug("Ignoring msg for unknown network %s.", msg['network'])
        except Network.DoesNotExist:
            log.error("Network %s not found in DB.", msg['network'])
        except Backend.DoesNotExist:
            log.error("Backend %s not found in DB.", msg['cluster'])
        except BackendNetwork.DoesNotExist:
            log.error("Network %s on backend %s not found in DB.",
                      msg['network'], msg['cluster'])
    return wrapper


def if_update_required(func):
    """
    Decorator for checking if an incoming message needs to update the db.

    The database will not be updated in the following cases:
    - The message has been redelivered and the action has already been
      completed. In this case the event_time will be equal with the one
      in the database.
    - The message describes a previous state in the ganeti, from the one that
      is described in the db. In this case the event_time will be smaller from
      the one in the database.

    """
    @wraps(func)
    def wrapper(target, msg):
        try:
            event_time = merge_time(msg['event_time'])
        except:
            log.error("Received message with malformed time: %s",
                      msg['event_time'])
            raise KeyError

        db_time = target.backendtime

        if db_time and event_time <= db_time:
            format_ = "%d/%m/%y %H:%M:%S:%f"
            log.debug("Ignoring message %s.\nevent_timestamp: %s"
                      " db_timestamp: %s",
                      msg,
                      event_time.strftime(format_),
                      db_time.strftime(format_))
            return
        # New message. Update the database!
        func(target, msg, event_time)

    return wrapper


@instance_from_msg
@if_update_required
def update_db(vm, msg, event_time):
    """Process a notification of type 'ganeti-op-status'"""
    log.debug("Processing ganeti-op-status msg: %s", msg)

    if msg['type'] != "ganeti-op-status":
        log.error("Message is of unknown type %s.", msg['type'])
        return

    nics = msg.get("nics", None)
    beparams = msg.get("beparams", None)
    backend_mod.process_op_status(vm, event_time, msg['jobId'],
                                  msg['operation'], msg['status'],
                                  msg['logmsg'], nics=nics,
                                  beparams=beparams)

    log.debug("Done processing ganeti-op-status msg for vm %s.",
              msg['instance'])


@network_from_msg
@if_update_required
def update_network(network, msg, event_time):
    """Process a notification of type 'ganeti-network-status'"""
    log.debug("Processing ganeti-network-status msg: %s", msg)

    if msg['type'] != "ganeti-network-status":
        log.error("Message is of unknown type %s.", msg['type'])
        return

    opcode = msg['operation']
    status = msg['status']
    jobid = msg['jobId']

    if opcode == "OP_NETWORK_SET_PARAMS":
        backend_mod.process_network_modify(network, event_time, jobid, opcode,
                                           status, msg['add_reserved_ips'])
    else:
        backend_mod.process_network_status(network, event_time, jobid, opcode,
                                           status, msg['logmsg'])

    log.debug("Done processing ganeti-network-status msg for network %s.",
              msg['network'])


@instance_from_msg
@if_update_required
def update_build_progress(vm, msg, event_time):
    """
    Process a create progress message. Update build progress, or create
    appropriate diagnostic entries for the virtual machine instance.
    """
    log.debug("Processing ganeti-create-progress msg: %s", msg)

    if msg['type'] not in ('image-copy-progress', 'image-error', 'image-info',
                           'image-warning', 'image-helper'):
        log.error("Message is of unknown type %s", msg['type'])
        return

    if msg['type'] == 'image-copy-progress':
        backend_mod.process_create_progress(vm, event_time, msg['progress'])
        # we do not add diagnostic messages for copy-progress messages
        return

    # default diagnostic fields
    source = msg['type']
    level = 'DEBUG'
    message = msg.get('messages', '')
    if isinstance(message, list):
        message = " ".join(message)

    details = msg.get('stderr', None)

    if msg['type'] == 'image-helper':
        # for helper task events join subtype to diagnostic source and
        # set task name as diagnostic message
        if msg.get('subtype', None):
            if msg.get('subtype') in ['task-start', 'task-end']:
                message = msg.get('task', message)
                source = "%s-%s" % (source, msg.get('subtype'))

        if msg.get('subtype', None) == 'warning':
            level = 'WARNING'

        if msg.get('subtype', None) == 'error':
            level = 'ERROR'

        if msg.get('subtype', None) == 'info':
            level = 'INFO'

    if msg['type'] == 'image-error':
        level = 'ERROR'

    if msg['type'] == 'image-warning':
        level = 'WARNING'

    if not message.strip():
        message = " ".join(source.split("-")).capitalize()

    # create the diagnostic entry
    backend_mod.create_instance_diagnostic(vm, message, source, level,
                                           event_time, details=details)

    log.debug("Done processing ganeti-create-progress msg for vm %s.",
              msg['instance'])


@handle_message_delivery
@transaction.commit_on_success()
def update_cluster(msg):
    clustername = msg.get("cluster")
    if clustername is None:
        return
    backend = Backend.objects.select_for_update().get(clustername=clustername)
    backend_mod.update_backend_disk_templates(backend)
    backend_mod.update_backend_resources(backend)


def dummy_proc(client, message, *args, **kwargs):
    try:
        log.debug("Msg: %s", message['body'])
        client.basic_ack(message)
    except Exception as e:
        log.exception("Could not receive message %s" % e)
