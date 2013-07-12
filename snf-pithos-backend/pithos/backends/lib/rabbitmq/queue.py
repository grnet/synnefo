# Copyright 2012 GRNET S.A. All rights reserved.
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

import json
from hashlib import sha1
from random import random
from time import time

from synnefo.lib.amqp import AMQPClient


class Message(object):
    def __init__(self, client, user, instance, resource, value, details={}):
        self.eventVersion = '1.0'
        self.occurredMillis = int(time() * 1000)
        self.receivedMillis = self.occurredMillis
        self.clientID = client
        self.userID = user
        self.instanceID = instance
        self.resource = resource
        self.value = value
        self.details = details
        hash = sha1()
        hash.update(json.dumps(
            [client, user, resource, value, details, random()]))
        self.id = hash.hexdigest()


class Queue(object):
    """Queue.
       Required constructor parameters: hosts, exchange, client_id.
    """

    def __init__(self, **params):
        hosts = params['hosts']
        self.exchange = params['exchange']
        self.client_id = params['client_id']

        self.client = AMQPClient(hosts=hosts)
        self.client.connect()

        self.client.exchange_declare(exchange=self.exchange,
                                     type='topic')

    def send(self, message_key, user, instance, resource, value, details):
        body = Message(
            self.client_id, user, instance, resource, value, details)
        self.client.basic_publish(exchange=self.exchange,
                                  routing_key=message_key,
                                  body=json.dumps(body.__dict__))

    def close(self):
        self.client.close()
