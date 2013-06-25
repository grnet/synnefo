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

from haigha.connections import RabbitConnection
from haigha.message import Message
from haigha import exceptions
from random import shuffle
from time import sleep
import logging
import socket
from synnefo import settings
from synnefo.lib.ordereddict import OrderedDict
import gevent
from gevent import monkey
from functools import wraps


logging.basicConfig(level=logging.INFO,
                    format="[%(levelname)s %(asctime)s] %(message)s")
logger = logging.getLogger('haigha')

sock_opts = {
    (socket.IPPROTO_TCP, socket.TCP_NODELAY): 1,
}


def reconnect_decorator(func):
    """
    Decorator for persistent connection with one or more AMQP brokers.

    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
        except (socket.error, exceptions.ConnectionError) as e:
            logger.error('Connection Closed while in %s: %s', func.__name__, e)
            self.connect()

    return wrapper


class AMQPHaighaClient():
    def __init__(self, hosts=settings.AMQP_HOSTS, max_retries=30,
                 confirms=True, confirm_buffer=200):
        self.hosts = hosts
        shuffle(self.hosts)

        self.max_retries = max_retries
        self.confirms = confirms
        self.confirm_buffer = confirm_buffer

        self.connection = None
        self.channel = None
        self.consumers = {}
        self.unacked = OrderedDict()

    def connect(self, retries=0):
        if retries > self.max_retries:
            logger.error("Aborting after %s retries", retries - 1)
            raise AMQPConnectionError('Aborting after %d connection failures.'
                                      % (retries - 1))
            return

        # Pick up a host
        host = self.hosts.pop()
        self.hosts.insert(0, host)

        #Patch gevent
        monkey.patch_all()

        try:
            self.connection = \
                RabbitConnection(logger=logger, debug=True,
                                 user='rabbit', password='r@bb1t',
                                 vhost='/', host=host,
                                 heartbeat=None,
                                 sock_opts=sock_opts,
                                 transport='gevent')
        except socket.error as e:
            logger.error('Cannot connect to host %s: %s', host, e)
            if retries > 2 * len(self.hosts):
                sleep(1)
            return self.connect(retries + 1)

        logger.info('Successfully connected to host: %s', host)

        logger.info('Creating channel')
        self.channel = self.connection.channel()

        if self.confirms:
            self._confirm_select()

        if self.unacked:
            self._resend_unacked_messages()

        if self.consumers:
            for queue, callback in self.consumers.items():
                self.basic_consume(queue, callback)

    def exchange_declare(self, exchange, type='direct'):
        """Declare an exchange
        @type exchange_name: string
        @param exchange_name: name of the exchange
        @type exchange_type: string
        @param exhange_type: one of 'direct', 'topic', 'fanout'

        """

        logger.info('Declaring %s exchange: %s', type, exchange)
        self.channel.exchange.declare(exchange, type,
                                      auto_delete=False, durable=True)

    def queue_declare(self, queue, exclusive=False, mirrored=True,
                      mirrored_nodes='all'):
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

        self.channel.queue.declare(queue, durable=True, exclusive=exclusive,
                                   auto_delete=False, arguments=arguments)

    def queue_bind(self, queue, exchange, routing_key):
        logger.info('Binding queue %s to exchange %s with key %s', queue,
                    exchange, routing_key)
        self.channel.queue.bind(queue=queue, exchange=exchange,
                                routing_key=routing_key)

    def _confirm_select(self):
        logger.info('Setting channel to confirm mode')
        self.channel.confirm.select()
        self.channel.basic.set_ack_listener(self._ack_received)
        self.channel.basic.set_nack_listener(self._nack_received)

    @reconnect_decorator
    def basic_publish(self, exchange, routing_key, body):
        msg = Message(body, delivery_mode=2)
        mid = self.channel.basic.publish(msg, exchange, routing_key)
        if self.confirms:
            self.unacked[mid] = (exchange, routing_key, body)
            if len(self.unacked) > self.confirm_buffer:
                self.get_confirms()

        logger.debug('Published message %s with id %s', body, mid)

    @reconnect_decorator
    def get_confirms(self):
        self.connection.read_frames()

    @reconnect_decorator
    def _resend_unacked_messages(self):
        msgs = self.unacked.values()
        self.unacked.clear()
        for exchange, routing_key, body in msgs:
            logger.debug('Resending message %s', body)
            self.basic_publish(exchange, routing_key, body)

    @reconnect_decorator
    def _ack_received(self, mid):
        print mid
        logger.debug('Received ACK for message with id %s', mid)
        self.unacked.pop(mid)

    @reconnect_decorator
    def _nack_received(self, mid):
        logger.error('Received NACK for message with id %s. Retrying.', mid)
        (exchange, routing_key, body) = self.unacked[mid]
        self.basic_publish(exchange, routing_key, body)

    def basic_consume(self, queue, callback):
        """Consume from a queue.

        @type queue: string or list of strings
        @param queue: the name or list of names from the queues to consume
        @type callback: function
        @param callback: the callback function to run when a message arrives

        """

        self.consumers[queue] = callback
        self.channel.basic.consume(queue, consumer=callback, no_ack=False)

    @reconnect_decorator
    def basic_wait(self):
        """Wait for messages from the queues declared by basic_consume.

        This function will block until a message arrives from the queues that
        have been declared with basic_consume. If the optional arguments
        'promise' is given, only messages for this promise will be delivered.

        """

        self.connection.read_frames()
        gevent.sleep(0)

    @reconnect_decorator
    def basic_get(self, queue):
        self.channel.basic.get(queue, no_ack=False)

    @reconnect_decorator
    def basic_ack(self, message):
        delivery_tag = message.delivery_info['delivery_tag']
        self.channel.basic.ack(delivery_tag)

    @reconnect_decorator
    def basic_nack(self, message):
        delivery_tag = message.delivery_info['delivery_tag']
        self.channel.basic.ack(delivery_tag)

    def close(self):
        try:
            if self.confirms:
                while self.unacked:
                    print self.unacked
                    self.get_confirms()
            self.channel.close()
            close_info = self.channel.close_info
            logger.info('Successfully closed channel. Info: %s', close_info)
            self.connection.close()
        except socket.error as e:
            logger.error('Connection closed while closing connection:%s', e)

    def queue_delete(self, queue, if_unused=True, if_empty=True):
        self.channel.queue.delete(queue, if_unused, if_empty)

    def exchange_delete(self, exchange, if_unused=True):
        self.channel.exchange.delete(exchange, if_unused)

    def basic_class(self):
        pass


class AMQPConnectionError():
    pass
