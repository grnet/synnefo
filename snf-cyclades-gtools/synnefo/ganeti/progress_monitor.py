#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011, 2012 GRNET S.A. All rights reserved.
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
