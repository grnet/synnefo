#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""Utility to monitor the progress of image deployment

A small utility that collects various monitoring messages from snf-image and
forwards them to the rest of the Synnefo infrastructure over AMQP.
"""

import os
import sys
import time
import json

from synnefo import settings
from synnefo.lib.amqp import AMQPClient
from synnefo.lib.utils import split_time

PROGNAME = os.path.basename(sys.argv[0])


def jsonstream(file):
    buf = ""
    decoder = json.JSONDecoder()
    while True:
        new_data = os.read(file.fileno(), 512)
        if not len(new_data):
            break

        buf += new_data.strip()
        while 1:
            try:
                msg, idx = decoder.raw_decode(buf)
            except ValueError:
                break
            yield msg
            buf = buf[idx:].strip()


def main():

    usage = "Usage: %s <instance_name>\n" % PROGNAME

    if len(sys.argv) != 2:
        sys.stderr.write(usage)
        return 1

    instance_name = sys.argv[1]

    # WARNING: This assumes that instance names
    # are of the form prefix-id, and uses prefix to
    # determine the routekey for AMPQ
    prefix = instance_name.split('-')[0]
    routekey = "ganeti.%s.event.progress" % prefix
    amqp_client = AMQPClient(confirm_buffer=10)
    amqp_client.connect()
    amqp_client.exchange_declare(settings.EXCHANGE_GANETI, "topic")

    for msg in jsonstream(sys.stdin):
        msg['event_time'] = split_time(time.time())
        msg['instance'] = instance_name

        # log to stderr
        sys.stderr.write("[MONITOR] %s\n" % json.dumps(msg))

        # then send it over AMQP
        amqp_client.basic_publish(exchange=settings.EXCHANGE_GANETI,
                                  routing_key=routekey,
                                  body=json.dumps(msg))

    amqp_client.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
