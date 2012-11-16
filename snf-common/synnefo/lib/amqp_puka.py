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

""" Module implementing connection and communication with an AMQP broker.

AMQP Client's implemented by this module silenty detect connection failures and
try to reconnect to any available broker. Also publishing takes advantage of
publisher-confirms in order to guarantee that messages are properly delivered
to the broker.

"""

import logging

from puka import Client
from puka import spec_exceptions
import socket
from socket import error as socket_error
from time import sleep
from random import shuffle
from functools import wraps
from ordereddict import OrderedDict
from synnefo import settings

logger = logging.getLogger("amqp")


def reconnect_decorator(func):
    """
    Decorator for persistent connection with one or more AMQP brokers.

    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (socket_error, spec_exceptions.ConnectionForced) as e:
            logger.error('Connection Closed while in %s: %s', func.__name__, e)
            self.connect()

    return wrapper


class AMQPPukaClient(object):
    """
    AMQP generic client implementing most of the basic AMQP operations.

    """
    def __init__(self, hosts=settings.AMQP_HOSTS, max_retries=30,
                 confirms=True, confirm_buffer=100):
        """
        Format hosts as "amqp://username:pass@host:port"
        max_retries=0 defaults to unlimited retries

        """

        self.hosts = hosts
        shuffle(self.hosts)

        self.max_retries = max_retries
        self.confirms = confirms
        self.confirm_buffer = confirm_buffer

        self.connection = None
        self.channel = None
        self.consumers = {}
        self.unacked = OrderedDict()
        self.unsend = OrderedDict()
        self.consume_promises = []
        self.exchanges = []

    def connect(self, retries=0):
        if self.max_retries and retries >= self.max_retries:
            logger.error("Aborting after %d retries", retries)
            raise AMQPConnectionError('Aborting after %d connection failures.'\
                                      % retries)
            return

        # Pick up a host
        host = self.hosts.pop()
        self.hosts.insert(0, host)

        self.client = Client(host, pubacks=self.confirms)

        host = host.split('@')[-1]
        logger.debug('Connecting to node %s' % host)

        try:
            promise = self.client.connect()
            self.client.wait(promise)
        except socket_error as e:
            if retries < len(self.hosts):
                logger.warning('Cannot connect to host %s: %s', host, e)
            else:
                logger.error('Cannot connect to host %s: %s', host, e)
                sleep(1)
            return self.connect(retries + 1)

        logger.info('Successfully connected to host: %s', host)

        # Setup TCP keepalive option
        self.client.sd.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # Keepalive time
        self.client.sd.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 20)
        # Keepalive interval
        self.client.sd.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 2)
        # Keepalive retry
        self.client.sd.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 10)

        logger.info('Creating channel')

        # Clear consume_promises each time connecting, since they are related
        # to the connection object
        self.consume_promises = []

        if self.unacked:
            self._resend_unacked_messages()

        if self.unsend:
            self._resend_unsend_messages()

        if self.consumers:
            for queue, callback in self.consumers.items():
                self.basic_consume(queue, callback)

        if self.exchanges:
            exchanges = self.exchanges
            self.exchanges = []
            for exchange, type in exchanges:
                self.exchange_declare(exchange, type)

    @reconnect_decorator
    def reconnect(self):
        self.close()
        self.connect()

    def exchange_declare(self, exchange, type='direct'):
        """Declare an exchange
        @type exchange_name: string
        @param exchange_name: name of the exchange
        @type exchange_type: string
        @param exhange_type: one of 'direct', 'topic', 'fanout'

        """
        logger.info('Declaring %s exchange: %s', type, exchange)
        promise = self.client.exchange_declare(exchange=exchange,
                                               type=type,
                                               durable=True,
                                               auto_delete=False)
        self.client.wait(promise)
        self.exchanges.append((exchange, type))

    @reconnect_decorator
    def queue_declare(self, queue, exclusive=False,
                      mirrored=True, mirrored_nodes='all',
                      dead_letter_exchange=None):
        """Declare a queue

        @type queue: string
        @param queue: name of the queue
        @param mirrored: whether the queue will be mirrored to other brokers
        @param mirrored_nodes: the policy for the mirrored queue.
            Available policies:
                - 'all': The queue is mirrored to all nodes and the
                  master node is the one to which the client is
                  connected
                - a list of nodes. The queue will be mirrored only to
                  the specified nodes, and the master will be the
                  first node in the list. Node names must be provided
                  and not host IP. example: [node1@rabbit,node2@rabbit]

        """
        logger.info('Declaring queue: %s', queue)

        if mirrored:
            if mirrored_nodes == 'all':
                arguments = {'x-ha-policy': 'all'}
            elif isinstance(mirrored_nodes, list):
                arguments = {'x-ha-policy': 'nodes',
                           'x-ha-policy-params': mirrored_nodes}
            else:
                raise AttributeError
        else:
            arguments = {}

        if dead_letter_exchange:
            arguments['x-dead-letter-exchange'] = dead_letter_exchange

        promise = self.client.queue_declare(queue=queue, durable=True,
                                            exclusive=exclusive,
                                            auto_delete=False,
                                            arguments=arguments)
        self.client.wait(promise)

    def queue_bind(self, queue, exchange, routing_key):
        logger.debug('Binding queue %s to exchange %s with key %s'
                 % (queue, exchange, routing_key))
        promise = self.client.queue_bind(exchange=exchange, queue=queue,
                                         routing_key=routing_key)
        self.client.wait(promise)

    @reconnect_decorator
    def basic_publish(self, exchange, routing_key, body, headers={}):
        """Publish a message with a specific routing key """
        self._publish(exchange, routing_key, body, headers)

        self.flush_buffer()

        if self.confirms and len(self.unacked) >= self.confirm_buffer:
            self.get_confirms()

    @reconnect_decorator
    def basic_publish_multi(self, exchange, routing_key, bodies):
        for body in bodies:
            self.unsend[body] = (exchange, routing_key)

        for body in bodies:
            self._publish(exchange, routing_key, body)
            self.unsend.pop(body)

        self.flush_buffer()

        if self.confirms:
            self.get_confirms()

    def _publish(self, exchange, routing_key, body, headers={}):
        # Persisent messages by default!
        headers['delivery_mode'] = 2
        promise = self.client.basic_publish(exchange=exchange,
                                            routing_key=routing_key,
                                            body=body, headers=headers)

        if self.confirms:
            self.unacked[promise] = (exchange, routing_key, body)

        return promise

    @reconnect_decorator
    def flush_buffer(self):
        while self.client.needs_write():
            self.client.on_write()

    @reconnect_decorator
    def get_confirms(self):
        for promise in self.unacked.keys():
            self.client.wait(promise)
            self.unacked.pop(promise)

    @reconnect_decorator
    def _resend_unacked_messages(self):
        """Resend unacked messages in case of a connection failure."""
        msgs = self.unacked.values()
        self.unacked.clear()
        for exchange, routing_key, body in msgs:
            logger.debug('Resending message %s' % body)
            self.basic_publish(exchange, routing_key, body)

    @reconnect_decorator
    def _resend_unsend_messages(self):
        """Resend unsend messages in case of a connection failure."""
        for body in self.unsend.keys():
            (exchange, routing_key) = self.unsend[body]
            self.basic_publish(exchange, routing_key, body)
            self.unsend.pop(body)

    @reconnect_decorator
    def basic_consume(self, queue, callback, prefetch_count=0):
        """Consume from a queue.

        @type queue: string or list of strings
        @param queue: the name or list of names from the queues to consume
        @type callback: function
        @param callback: the callback function to run when a message arrives

        """
        # Store the queues and the callback
        self.consumers[queue] = callback

        def handle_delivery(promise, msg):
            """Hide promises and messages without body"""
            if 'body' in msg:
                callback(self, msg)
            else:
                logger.debug("Message without body %s" % msg)
                raise socket_error

        consume_promise = \
                self.client.basic_consume(queue=queue,
                                          prefetch_count=prefetch_count,
                                          callback=handle_delivery)

        self.consume_promises.append(consume_promise)
        return consume_promise

    @reconnect_decorator
    def basic_wait(self, promise=None, timeout=0):
        """Wait for messages from the queues declared by basic_consume.

        This function will block until a message arrives from the queues that
        have been declared with basic_consume. If the optional arguments
        'promise' is given, only messages for this promise will be delivered.

        """
        if promise is not None:
            return self.client.wait(promise, timeout)
        else:
            return self.client.wait(self.consume_promises, timeout)

    @reconnect_decorator
    def basic_get(self, queue):
        """Get a single message from a queue.

        This is a non-blocking method for getting messages from a queue.
        It will return None if the queue is empty.

        """
        get_promise = self.client.basic_get(queue=queue)
        result = self.client.wait(get_promise)
        if 'empty' in result:
            # The queue is empty
            return None
        else:
            return result

    @reconnect_decorator
    def basic_ack(self, message):
        self.client.basic_ack(message)

    @reconnect_decorator
    def basic_nack(self, message):
        self.client.basic_ack(message)

    @reconnect_decorator
    def basic_reject(self, message, requeue=False):
        """Reject a message.

        If requeue option is False and a dead letter exchange is associated
        with the queue, the message will be routed to the dead letter exchange.

        """
        self.client.basic_reject(message, requeue=requeue)

    def close(self):
        """Check that messages have been send and close the connection."""
        logger.debug("Closing connection to %s", self.client.host)
        try:
            if self.confirms:
                self.get_confirms()
            close_promise = self.client.close()
            self.client.wait(close_promise)
        except (socket_error, spec_exceptions.ConnectionForced) as e:
            logger.error('Connection closed while closing connection:%s',
                          e)

    def queue_delete(self, queue, if_unused=True, if_empty=True):
        """Delete a queue.

        Returns False if the queue does not exist
        """
        try:
            promise = self.client.queue_delete(queue=queue,
                                               if_unused=if_unused,
                                               if_empty=if_empty)
            self.client.wait(promise)
            return True
        except spec_exceptions.NotFound:
            logger.info("Queue %s does not exist", queue)
            return False

    def exchange_delete(self, exchange, if_unused=True):
        """Delete an exchange."""
        try:

            promise = self.client.exchange_delete(exchange=exchange,
                                                  if_unused=if_unused)
            self.client.wait(promise)
            return True
        except spec_exceptions.NotFound:
            logger.info("Exchange %s does not exist", exchange)
            return False

    @reconnect_decorator
    def basic_cancel(self, promise=None):
        """Cancel consuming from a queue. """
        if promise is not None:
            self.client.basic_cancel(promise)
        else:
            for promise in self.consume_promises:
                self.client.basic_cancel(promise)


class AMQPConnectionError(Exception):
    pass
