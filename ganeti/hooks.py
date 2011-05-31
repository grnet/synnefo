#!/usr/bin/env python
#
# Copyright (c) 2010 Greek Research and Technology Network
#
"""Ganeti hooks for Synnefo

These are the individual Ganeti hooks for Synnefo.

"""

import sys
import os

import time
import json
import socket
import logging

from amqplib import client_0_8 as amqp

import synnefo.settings as settings


def ganeti_net_status(logger, environ):
    """Produce notifications of type 'Ganeti-net-status'
    
    Process all GANETI_INSTANCE_NICx_y environment variables,
    where x is the NIC index, starting at 0,
    and y is one of "MAC", "IP".

    The result is returned as a single notification message
    of type 'Ganeti-net-status', detailing the NIC configuration
    of a Ganeti instance.

    """
    nics = {}

    key_to_attr = { 'IP': 'ip', 'MAC': 'mac', 'BRIDGE': 'link' }

    for env in environ.keys():
        if env.startswith("GANETI_INSTANCE_NIC"):
            s = env.replace("GANETI_INSTANCE_NIC", "").split('_', 1)
            if len(s) == 2 and s[0].isdigit() and s[1] in ('MAC', 'IP', 'BRIDGE'):
                index = int(s[0])
                key = key_to_attr[s[1]]

                if nics.has_key(index):
                    nics[index][key] = environ[env]
                else:
                    nics[index] = { key: environ[env] }

    # Verify our findings are consistent with the Ganeti environment
    indexes = list(nics.keys())
    ganeti_nic_count = int(environ['GANETI_INSTANCE_NIC_COUNT'])
    if len(indexes) != ganeti_nic_count:
        logger.error("I have %d NICs, Ganeti says number of NICs is %d",
            len(indexes), ganeti_nic_count)
        raise Exception("Inconsistent number of NICs in Ganeti environment")

    if indexes != range(0, len(indexes)):
        logger.error("Ganeti NIC indexes are not consecutive starting at zero.");
        logger.error("NIC indexes are: %s. Environment is: %s", indexes, environ)
        raise Exception("Unexpected inconsistency in the Ganeti environment")

    # Construct the notification
    instance = environ['GANETI_INSTANCE_NAME']

    nics_list = []
    for i in indexes:
        nics_list.append(nics[i])

    msg = {
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

    def on_master(self):
        """Return True if running on the Ganeti master"""
        return socket.getfqdn() == self.environ['GANETI_MASTER']

    def publish_msgs(self, msgs):
        for (msgtype, msg) in msgs:
            routekey = "ganeti.%s.event.%s" % (self.prefix, msgtype)
            self.logger.debug("Pushing message to RabbitMQ: %s (key = %s)",
                json.dumps(msg), routekey)
            msg = amqp.Message(json.dumps(msg))
            msg.properties["delivery_mode"] = 2  # Persistent

            # Retry up to five times to open a channel to RabbitMQ.
            # The hook needs to abort if this count is exceeded, because it
            # runs synchronously with VM creation inside Ganeti, and may only
            # run for a finite amount of time.
            #
            # FIXME: We need a reconciliation mechanism between the DB and
            #        Ganeti, for cases exactly like this.
            conn = None
            sent = False
            retry = 0
            while not sent and retry < 5:
                self.logger.debug("Attempting to publish to RabbitMQ at %s",
                    settings.RABBIT_HOST)
                try:
                    if not conn:
                        conn = amqp.Connection(host=settings.RABBIT_HOST,
                            userid=settings.RABBIT_USERNAME,
                            password=settings.RABBIT_PASSWORD,
                            virtual_host=settings.RABBIT_VHOST)
                        chann = conn.channel()
                        self.logger.debug("Successfully connected to RabbitMQ at %s",
                            settings.RABBIT_HOST)

                    chann.basic_publish(msg,
                        exchange=settings.EXCHANGE_GANETI,
                        routing_key=routekey)
                    sent = True
                    self.logger.debug("Successfully sent message to RabbitMQ")
                except socket.error:
                    conn = False
                    retry += 1
                    self.logger.exception("Publish to RabbitMQ failed, retry=%d in 1s",
                        retry)
                    time.sleep(1)

            if not sent:
                raise Exception("Publish to RabbitMQ failed after %d tries, aborting" % retry)


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
            notifs.append(("net", ganeti_net_status(self.logger, self.environ)))
            
            self.publish_msgs(notifs)

        return 0


class PostStopHook(GanetiHook):
    def run(self):
        return 0

