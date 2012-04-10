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

import puka
import logging
import socket

from time import sleep
from random import shuffle
from functools import wraps

from ordereddict import OrderedDict
from synnefo import settings

AMQP_HOSTS = settings.AMQP_HOSTS

MAX_RETRIES = 20

log = logging.getLogger()


def reconnect_decorator(func):
    """
    Decorator for persistent connection with one or more AMQP brokers.

    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            if self.client.sd is None:
                self.connect()
            return func(self, *args, **kwargs)
        except (socket.error, puka.spec_exceptions.ConnectionForced):
            log.debug("Connection closed. Reconnecting")
            self.connect()
            return wrapper(self, *args, **kwargs)
        except Exception:
            if self.client.sd is None:
                log.debug("Connection closed. Reconnecting")
                self.connect()
                return wrapper(self, *args, **kwargs)
            else:
                raise
    return wrapper


class AMQPClient():
    """
    AMQP generic client implementing most of the basic AMQP operations.

    This client confirms delivery of each published message before publishing
    the next one, which results in low performance. Better performance can be
    achieved by using AMQPAsyncClient.

    """
    def __init__(self, hosts=AMQP_HOSTS, max_retries=MAX_RETRIES):
        """Format hosts as "amqp://username:pass@host:port" """
        # Shuffle the elements of the host list for better load balancing
        self.hosts = hosts
        shuffle(self.hosts)
        self.max_retries = max_retries

        self.promises = []
        self.consume_promises = []
        self.consume_info = {}

    def connect(self, retries=0):
        # Pick up a host
        url = self.hosts.pop()
        self.hosts.insert(0, url)

        if retries > self.max_retries:
            raise AMQPError("Cannot connect to any node after %s attemps" % retries)
        if retries > 2 * len(self.hosts):
            sleep(1)

        self.client = puka.Client(url, pubacks=True)

        host = url.split('@')[-1]
        log.debug('Connecting to node %s' % host)

        try:
            promise = self.client.connect()
            self.client.wait(promise)
        except socket.error as e:
            log.debug('Cannot connect to node %s.' % host)
            return self.connect(retries+1)

    @reconnect_decorator
    def exchange_declare(self, exchange_name, exchange_type='direct',
                         durable=True, auto_delete=False):
        """Declare an exchange
        @type exchange_name: string
        @param exchange_name: name of the exchange
        @type exchange_type: string
        @param exhange_type: one of 'direct', 'topic', 'fanout'

        """
        log.debug('Declaring exchange %s of %s type.'
                  %(exchange_name, exchange_type))
        promise = self.client.exchange_declare(exchange=exchange_name,
                                               type=exchange_type,
                                               durable=durable,
                                               auto_delete=auto_delete)
        self.client.wait(promise)
        log.debug('Exchange %s declared succesfully ' % exchange_name)

    @reconnect_decorator
    def queue_declare(self, queue, durable=True, exclusive=False,
                      auto_delete=False, mirrored=True, mirrored_nodes='all'):
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

        log.debug('Declaring queue %s' % queue)
        if mirrored:
            if mirrored_nodes == 'all':
                arguments={'x-ha-policy':'all'}
            elif isinstance(mirrored_nodes, list):
                arguments={'x-ha-policy':'nodes', 'x-ha-policy-params':mirrored_nodes}
            else:
                raise AttributeError
        else:
            arguments = {}

        promise = self.client.queue_declare(queue=queue, durable=durable,
                                            exclusive=exclusive,
                                            auto_delete=auto_delete,
                                            arguments=arguments)
        self.client.wait(promise)
        log.debug('Queue %s declared successfully.' % queue)

    @reconnect_decorator
    def queue_bind(self, queue, exchange, routing_key):
        log.debug('Binding queue %s to exchange %s with key %s'
                 % (queue, exchange, routing_key))
        promise = self.client.queue_bind(exchange=exchange, queue=queue,
                                         routing_key=routing_key)
        self.client.wait(promise)
        log.debug('Binding completed successfully')

    def basic_publish_multi(self, exhange, routing_key, msgs, headers={}):
        """Send many messages to the  same exchange and with the same key """
        for msg in msgs:
            self.basic_publish(exchange, routing_key, headers, msg)

    @reconnect_decorator
    def basic_publish(self, exchange, routing_key, body, headers={}):
        """Publish a message with a specific routing key """

        # Persisent messages by default!
        if not 'delivery_mode' in headers:
            headers['delivery_mode'] = 2

        promise = self.client.basic_publish(exchange=exchange,
                                            routing_key=routing_key,
                                            body=body, headers=headers)
        self.client.wait(promise)

    @reconnect_decorator
    def basic_consume(self, queue, callback, prefetch_count=0):
        """Consume from a queue.

        @type queue: string or list of strings
        @param queue: the name or list of names from the queues to consume
        @type callback: function
        @param callback: the callback function to run when a message arrives

        """
        if isinstance(queue, str):
            queue = [queue]
        elif isinstance(queue, list):
            pass
        else:
            raise AttributeError

        # Store the queues and the callback
        for q in queue:
            self.consume_info[q] = callback

        def handle_delivery(promise, result):
            """Hide promises and messages without body"""
            if 'body' in result:
                callback(self, result)
            else:
                log.debug("Message without body %s" % result)
                return

        consume_promise = \
                self.client.basic_consume_multi(queues=queue,
                                                prefetch_count=prefetch_count,
                                                callback=handle_delivery)
        self.consume_promises.append(consume_promise)
        return consume_promise

    def basic_wait(self, promise=None, timeout=0):
        """Wait for messages from the queues declared by basic_consume.

        This function will block until a message arrives from the queues that
        have been declared with basic_consume. If the optional arguments
        'promise' is given, only messages for this promise will be delivered.

        """
        try:
            if promise is not None:
               self.client.wait(promise, timeout)
            else:
               self.client.wait(self.consume_promises)
        except (socket.error, puka.spec_exceptions.ConnectionForced):
            log.debug('Connection closed while receiving messages.')
            self.consume_promises = []
            self.connect()
            for queues, callback in self.consume_info.items():
                self.basic_consume(queues, callback)
            self.basic_wait(timeout)
        except Exception as e:
            if self.client.sd is None:
                log.debug('Connection closed while receiving messages.')
                self.consume_promises = []
                self.connect()
                for queues, callback in self.consume_info.items():
                    self.basic_consume(queues, callback)
                self.basic_wait(timeout)
            else:
                log.error("Exception while waiting for messages ",e)
                raise

    def basic_cancel(self, promise=None):
        """Cancel consuming from a queue. """
        try:
            if promise is not None:
                self.client.basic_cancel(promise)
            else:
                for promise in self.consume_promises:
                    self.client.basic_cancel(promise)
        except (socket.error, puka.spec_exceptions.ConnectionForced):
            pass
        except Exception as e:
            if self.client.sd is None:
                pass;
            else:
                log.error("Exception while canceling client ",e)
                raise


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

    def basic_ack(self, message):
        """Acknowledge a message. """
        try:
            self.client.basic_ack(message)
            return True
        except (socket.error, puka.spec_exceptions.ConnectionForced):
            return False
        except Exception as e:
            if self.client.sd is None:
                return False
            else:
                log.error("Exception while acknowleding message ",e)
                raise

    def close(self):
        """Close the connection with the AMQP broker. """
        try:
            close_promise = self.client.close()
            self.client.wait(close_promise)
        except (socket.error, puka.spec_exceptions.ConnectionForced):
            pass

    def queue_delete(self, queue, if_unused=False, if_empty=False):
        """Delete a queue.

        Returns False if the queue does not exist
        """
        try:
            promise = self.client.queue_delete(queue=queue, if_unused=if_unused,
                                               if_empty=if_empty)
            self.client.wait(promise)
            return True
        except puka.spec_exceptions.NotFound:
            log.debug("Queue %s does not exist", queue)
            return False

    def exchange_delete(self, exchange, if_unused=False):
        """Delete an exchange."""
        try:

            promise = self.client.exchange_delete(exchange=exchange,
                                                  if_unused=if_unused)
            self.client.wait(promise)
            return True
        except puka.spec_exceptions.NotFound:
            log.debug("Exchange %s does not exist", exchange)
            return False



class AMQPAsyncClient(AMQPClient):
    """AMQP client implementing asynchronous sending of messages.

    This client is more efficient that AMQPClient in sending large number
    of messages. Messages are confirmed to be sent to the broker in batches
    of a size specified by the 'max_buffer' argument.

    Messages are kept to an internal buffer until the max_buffer messages are
    sent or until the connection closes. Explicit delivering of messages can be
    achieved by calling 'wait_for_promises' method.

    Always remember to close the connection, or messages may be lost.

    """
    def __init__(self, hosts=AMQP_HOSTS, max_buffer=5000,
                 max_retries=MAX_RETRIES):
        AMQPClient.__init__(self, hosts, max_retries)
        self.published_msgs = OrderedDict()
        self._promise_counter = 0
        self.max_buffer=max_buffer

    def basic_publish_multi(self, exhange, routing_key, msgs, headers={}):
        while msgs:
            msg = msgs.pop[0]
            self.basic_publish(exchange, routing_key, msg, headers)

    def basic_publish(self, exchange, routing_key, body, headers={}):
        """Publish a message.

        The message will not be actually published to the broker until
        'max_buffer' messages are published or wait_for_promises is called.

        """
        try:
            if not 'delivery_mode' in headers:
                headers['delivery_mode'] = 2

            promise = self.client.basic_publish(exchange=exchange,
                                                routing_key=routing_key,
                                                body=body,
                                                headers=headers)

            self._promise_counter += 1
            self.published_msgs[promise] = {'exchange':exchange,
                                            'routing_key':routing_key,
                                            'body':body,
                                            'headers':headers}

            if self._promise_counter > self.max_buffer:
                self.wait_for_promises()

        except (socket.error, puka.spec_exceptions.ConnectionForced):
            log.debug('Connection closed while sending message %s.\
                      Reconnecting and retrying' % body)
            self.connect()
            self.basic_publish(exchange, routing_key, body, headers)
            return self._retry_publish_msgs()
        except Exception as e:
            if self.client.sd is None:
                log.debug('Connection closed while sending message %s.\
                             Reconnecting and retrying' % body)
                self.connect()
                self.basic_publish(exchange, routing_key, body, headers)
                return self._retry_publish_msgs()
            else:
                log.error("Exception while publishing message ",e)
                raise

    def wait_for_promises(self):
        """Wait for confirm that all messages are sent."""
        try:
            promises = self.published_msgs.keys()
            for promise in promises:
                self.client.wait(promise)
                self.published_msgs.pop(promise)
            self._promise_counter = 0
        except (socket.error, puka.spec_exceptions.ConnectionForced):
            log.debug('Connection closed while waiting from promises')
            self.connect()
            self._retry_publish_msgs()
        except Exception as e:
            if self.client.sd is None:
                log.debug('Connection closed while waiting from promises')
                self.connect()
                self._retry_publish_msgs()
            else:
                log.error("Exception while waiting for promises ",e)
                raise

    def _retry_publish_msgs(self):
        """Resend messages in case of a connection failure."""
        values = self.published_msgs.values()
        self.published_msgs = OrderedDict()
        for message in values:
            exchange = message['exchange']
            key = message['routing_key']
            body = message['body']
            headers = message['headers']
            log.debug('Resending message %s' % body)
            self.basic_publish(exchange, key, body, headers)

    def close(self):
        """Check that messages have been send and close the connection."""
        try:
            self.wait_for_promises()
            close_promise = self.client.close()
            self.client.wait(close_promise)
        except (socket.error, puka.spec_exceptions.ConnectionForced):
            pass
        except Exception as e:
            if self.client.sd is None:
                pass
            else:
                log.error("Exception while closing the connection ",e)
                raise

    def flush_buffer(self):
        try:
            self.client.on_write()
        except (socket.error, puka.spec_exceptions.ConnectionForced):
            log.debug('Connection closed while clearing buffer')
            self.connect()
            return self._retry_publish_msgs()
        except Exception as e:
            if self.client.sd is None:
                log.debug('Connection closed while clearing buffer')
                self.connect()
                return self._retry_publish_msgs()
            else:
                log.error("Exception while clearing buffer ",e)
                raise

class AMQPConsumer(AMQPClient):
    """AMQP client implementing a consumer without callbacks.

    """
    def __init__(self, hosts=AMQP_HOSTS, max_buffer=5000,
                 max_retries=MAX_RETRIES):
        AMQPClient.__init__(self, hosts, max_retries)
        self.consume_queues = []
        self.consume_promises = []

    @reconnect_decorator
    def basic_consume(self, queue, prefetch_count=0):
        """Consume from a queue.

        @type queue: string or list of strings
        @param queue: the name or list of names from the queues to consume
        @type callback: function
        @param callback: the callback function to run when a message arrives

        """
        if isinstance(queue, str):
            queue = [queue]
        elif isinstance(queue, list):
            pass
        else:
            raise AttributeError

        # Store the queues and the callback
        for q in queue:
            self.consume_queues.append(q)

        consume_promise = \
                self.client.basic_consume_multi(queues=queue,
                                                prefetch_count=prefetch_count)
        self.consume_promises.append(consume_promise)
        return consume_promise

    def basic_wait(self, promise=None, timeout=0):
        """Wait for messages from the queues declared by basic_consume.

        This function will block until a message arrives from the queues that
        have been declared with basic_consume. If the optional arguments
        'promise' is given, only messages for this promise will be delivered.

        """
        try:
            if promise is not None:
               return self.client.wait(promise, timeout)
            else:
               return self.client.wait(self.consume_promises)
        except (socket.error, puka.spec_exceptions.ConnectionForced):
            log.debug('Connection closed while receiving messages.')
            self.consume_promises = []
            self.connect()
            for queues in self.consume_queues:
                self.basic_consume(queues)
            self.basic_wait(timeout)
        except Exception as e:
            if self.client.sd is None:
                log.debug('Connection closed while receiving messages.')
                self.consume_promises = []
                self.connect()
                for queues in self.consume_queues:
                    self.basic_consume(queues)
                self.basic_wait(timeout)
            else:
                log.error("Exception while waiting for messages ",e)
                raise


class AMQPError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)
