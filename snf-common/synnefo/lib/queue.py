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

import pika
import json
import uuid

from urlparse import urlparse
from hashlib import sha1
from random import random
from time import time


def exchange_connect(exchange, vhost='/'):
    """Format exchange as a URI: rabbitmq://user:pass@host:port/exchange"""
    parts = urlparse(exchange)
    if parts.scheme != 'rabbitmq':
        return None
    if len(parts.path) < 2 or not parts.path.startswith('/'):
        return None
    exchange = parts.path[1:]
    connection = pika.BlockingConnection(pika.ConnectionParameters(
                    host=parts.hostname, port=parts.port, virtual_host=vhost,
                    credentials=pika.PlainCredentials(parts.username, parts.password)))
    channel = connection.channel()
    channel.exchange_declare(exchange=exchange, type='topic', durable=True)
    return (connection, channel, exchange)

def exchange_close(conn):
    connection, channel, exchange = conn
    connection.close()

def exchange_send(conn, key, value):
    """Messages are sent to exchanges at a key."""
    connection, channel, exchange = conn
    channel.basic_publish(exchange=exchange,
                          routing_key=key,
                          body=json.dumps(value))

    
def exchange_route(conn, key, queue):
    """Set up routing of keys to queue."""
    connection, channel, exchange = conn
    channel.queue_declare(queue=queue, durable=True,
                          exclusive=False, auto_delete=False)
    channel.queue_bind(exchange=exchange,
                       queue=queue,
                       routing_key=key)

def queue_callback(conn, queue, cb):
    
    def handle_delivery(channel, method_frame, header_frame, body):
        #print 'Basic.Deliver %s delivery-tag %i: %s' % (header_frame.content_type,
        #                                                method_frame.delivery_tag,
        #                                                body)
        if cb:
            cb(json.loads(body))
        channel.basic_ack(delivery_tag=method_frame.delivery_tag)
    
    connection, channel, exchange = conn
    channel.basic_consume(handle_delivery, queue=queue)

def queue_start(conn):
    connection, channel, exchange = conn
    channel.start_consuming()

class Receipt(object):
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
        hash.update(json.dumps([client, user, resource, value, details, random()]))
        self.id = hash.hexdigest()
    
    def format(self):
        return self.__dict__

class UserEvent(object):
    def __init__(self, client, user, is_active, eventType, details=None):
        self.eventVersion = '1'
        self.occurredMillis = int(time() * 1000)
        self.receivedMillis = self.occurredMillis
        self.clientID = client
        self.userID = user
        self.isActive = is_active
        self.role = 'default'
        self.eventType = eventType
        self.details = details or {}
        hash = sha1()
        hash.update(json.dumps([client,
                self.userID,
                self.isActive,
                self.role,
                self.eventType,
                self.details,
                self.occurredMillis
                ]
            )
        )
        self.id = hash.hexdigest()
    
    def format(self):
        return self.__dict__
