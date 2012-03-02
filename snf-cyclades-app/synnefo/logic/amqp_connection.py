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

import time
import socket

from logging import getLogger

from amqplib import client_0_8 as amqp
from django.conf import settings


log = getLogger('synnefo.logic')

_conn = None
_chan = None


def _connect():
    global _conn, _chan
    # Force the _conn object to re-initialize
    _conn = None
    retry = 0
    while _conn == None:
        try:
            _conn = amqp.Connection(host=settings.RABBIT_HOST,
                                   userid=settings.RABBIT_USERNAME,
                                   password=settings.RABBIT_PASSWORD,
                                   virtual_host=settings.RABBIT_VHOST)
        except socket.error:
            retry += 1
            if retry < 5 :
                log.exception("Cannot establish connection to AMQP. Retrying...")
                time.sleep(1)
            else:
                raise AMQPError("Queue error")
    _chan = _conn.channel()


def send(payload, exchange, key):
    """
        Send payload to the specified exchange using the provided routing key.

        This method will try reconnecting to the message server if a connection
        error occurs when sending the message. All other errors are forwarded
        to the client.
    """
    global _conn, _chan

    if payload is None:
        raise AMQPError("Message is empty")

    if exchange is None:
        raise AMQPError("Unknown exchange")

    if key is None:
        raise AMQPError("Unknown routing key")

    msg = amqp.Message(payload)
    msg.properties["delivery_mode"] = 2  # Persistent

    while True:
        try:
           _chan.basic_publish(msg,
                               exchange=exchange,
                               routing_key=key)
           return
        except socket.error as se:
           log.exception("Server went away, reconnecting...")
           _connect()
        except Exception as e:
            if _conn is None:
               _connect()
            else:
                log.exception('Caught unexpected exception (msg: %s)', msg)
                raise AMQPError("Error sending message to exchange %s with \
                                key %s.Payload: %s. Error was: %s",
                                (exchange, key, payload, e.message))


def __init__():
    _connect()

class AMQPError(Exception):
    pass
