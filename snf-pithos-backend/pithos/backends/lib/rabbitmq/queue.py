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
