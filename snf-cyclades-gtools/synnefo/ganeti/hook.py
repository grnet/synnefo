#!/usr/bin/env python
#
# -*- coding: utf-8 -*-
#
# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.
#
"""Ganeti hooks for Synnefo

These are the individual Ganeti hooks for Synnefo.

"""

import sys
import os
import json
import socket
import logging

from time import time

from synnefo import settings
from synnefo.lib.amqp import AMQPClient
from synnefo.lib.utils import split_time
from synnefo.util.mac2eui64 import mac2eui64


def ganeti_net_status(logger, environ):
    """Produce notifications of type 'Ganeti-net-status'

    Process all GANETI_INSTANCE_NICx_y environment variables,
    where x is the NIC index, starting at 0,
    and y is one of "MAC", "IP", "BRIDGE".

    The result is returned as a single notification message
    of type 'ganeti-net-status', detailing the NIC configuration
    of a Ganeti instance.

    """
    nics = {}

    key_to_attr = {'IP': 'ip',
                   'MAC': 'mac',
                   'BRIDGE': 'link',
                   'NETWORK': 'network'}

    for env in environ.keys():
        if env.startswith("GANETI_INSTANCE_NIC"):
            s = env.replace("GANETI_INSTANCE_NIC", "").split('_', 1)
            if len(s) == 2 and s[0].isdigit() and\
                    s[1] in ('MAC', 'IP', 'BRIDGE', 'NETWORK'):
                index = int(s[0])
                key = key_to_attr[s[1]]

                if index in nics:
                    nics[index][key] = environ[env]
                else:
                    nics[index] = {key: environ[env]}

                # IPv6 support:
                #
                # The IPv6 is derived using an EUI64 scheme.
                if key == 'mac':
                    subnet6 = environ.get("GANETI_INSTANCE_NIC" + s[0] +
                                          "_NETWORK_SUBNET6", None)
                    if subnet6:
                        nics[index]['ipv6'] = mac2eui64(nics[index]['mac'],
                                                        subnet6)

    # Amend notification with firewall settings
    tags = environ.get('GANETI_INSTANCE_TAGS', '')
    for tag in tags.split(' '):
        t = tag.split(':')
        if t[0:2] == ['synnefo', 'network']:
            if len(t) != 4:
                logger.error("Malformed synnefo tag %s", tag)
                continue
            try:
                index = int(t[2])
                nics[index]['firewall'] = t[3]
            except ValueError:
                logger.error("Malformed synnefo tag %s", tag)
            except KeyError:
                logger.error("Found tag %s for non-existent NIC %d",
                             tag, index)

    # Verify our findings are consistent with the Ganeti environment
    indexes = list(nics.keys())
    ganeti_nic_count = int(environ['GANETI_INSTANCE_NIC_COUNT'])
    if len(indexes) != ganeti_nic_count:
        logger.error("I have %d NICs, Ganeti says number of NICs is %d",
                     len(indexes), ganeti_nic_count)
        raise Exception("Inconsistent number of NICs in Ganeti environment")

    if indexes != range(0, len(indexes)):
        msg = "Ganeti NIC indexes are not consecutive starting at zero."
        logger.error(msg)
        msg = "NIC indexes are: %s. Environment is: %s" % (indexes, environ)
        logger.error(msg)
        raise Exception("Unexpected inconsistency in the Ganeti environment")

    # Construct the notification
    instance = environ['GANETI_INSTANCE_NAME']

    nics_list = []
    for i in indexes:
        nics_list.append(nics[i])

    msg = {
        "event_time": split_time(time()),
        "type": "ganeti-net-status",
        "instance": instance,
        "nics": nics_list
    }

    return msg


class GanetiHook():
    def __init__(self, logger, environ, instance, prefix):
        self.logger = logger
        self.environ = environ
        self.instance = instance
        self.prefix = prefix
        # Retry up to two times(per host) to open a channel to RabbitMQ.
        # The hook needs to abort if this count is exceeded, because it
        # runs synchronously with VM creation inside Ganeti, and may only
        # run for a finite amount of time.

        # FIXME: We need a reconciliation mechanism between the DB and
        #        Ganeti, for cases exactly like this.
        self.client = AMQPClient(hosts=settings.AMQP_HOSTS,
                                 max_retries=2 * len(settings.AMQP_HOSTS),
                                 logger=logger)
        self.client.connect()

    def on_master(self):
        """Return True if running on the Ganeti master"""
        return socket.getfqdn() == self.environ['GANETI_MASTER']

    def publish_msgs(self, msgs):
        for (msgtype, msg) in msgs:
            routekey = "ganeti.%s.event.%s" % (self.prefix, msgtype)
            self.logger.debug("Pushing message to RabbitMQ: %s (key = %s)",
                              json.dumps(msg), routekey)
            msg = json.dumps(msg)
            self.client.basic_publish(exchange=settings.EXCHANGE_GANETI,
                                      routing_key=routekey,
                                      body=msg)
        self.client.close()


class PostStartHook(GanetiHook):
    """Post-instance-startup Ganeti Hook.

    Produce notifications to the rest of the Synnefo
    infrastructure in the post-instance-start phase of Ganeti.

    Currently, this list only contains a single message,
    detailing the net configuration of an instance.

    This hook only runs on the Ganeti master.

    """
    def run(self):
        if self.on_master():
            notifs = []
            notifs.append(("net",
                           ganeti_net_status(self.logger, self.environ))
                          )

            self.publish_msgs(notifs)

        return 0


class PostStopHook(GanetiHook):
    def run(self):
        return 0


def main():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("synnefo.ganeti")

    try:
        instance = os.environ['GANETI_INSTANCE_NAME']
        op = os.environ['GANETI_HOOKS_PATH']
        phase = os.environ['GANETI_HOOKS_PHASE']
    except KeyError:
        raise Exception("Environment missing one of: "
                        "GANETI_INSTANCE_NAME, GANETI_HOOKS_PATH,"
                        " GANETI_HOOKS_PHASE")

    prefix = instance.split('-')[0]

    # FIXME: The hooks should only run for Synnefo instances.
    # Uncomment the following lines for a shared Ganeti deployment.
    # Currently, the following code is commented out because multiple
    # backend prefixes are used in the same Ganeti installation during
    # development.
    #if not instance.startswith(settings.BACKEND_PREFIX_ID):
    #    logger.warning("Ignoring non-Synnefo instance %s", instance)
    #    return 0

    hooks = {
        ("instance-add", "post"): PostStartHook,
        ("instance-start", "post"): PostStartHook,
        ("instance-reboot", "post"): PostStartHook,
        ("instance-stop", "post"): PostStopHook,
        ("instance-modify", "post"): PostStartHook
    }

    try:
        hook = hooks[(op, phase)](logger, os.environ, instance, prefix)
    except KeyError:
        raise Exception("No hook found for operation = '%s', phase = '%s'" %
                        (op, phase))
    return hook.run()

if __name__ == "__main__":
    sys.exit(main())
