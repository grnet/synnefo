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

import synnefo.settings as settings

def on_master(environ):
    """Return True if running on the Ganeti master"""
    return socket.getfqdn() == environ['GANETI_MASTER']

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

    for env in environ.keys():
        if env.startswith("GANETI_INSTANCE_NIC"):
            s = env.replace("GANETI_INSTANCE_NIC", "").split('_', 1)
            if len(s) == 2 and s[0].isdigit() and s[1] in ('MAC', 'IP'):
                index = int(s[0])
                key = s[1].lower()

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

def post_start_hook(logger, environ):
    """Construct notifications to the rest of Synnefo on instance startup.
    
    Currently, this list only contains a single message,
    detailing the net configuration of an instance.

    """
    notifs = []
    notifs.append(ganeti_net_status(logger, environ))

    print "post_start_hook: ", notifs
    return 0

def post_stop_hook(logger, environ):
    return 0

