#!/usr/bin/env python

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

import sys
import logging
import json

from synnefo.lib.amqp import AMQPClient

from optparse import OptionParser

from django.core.management import setup_environ
try:
    from synnefo import settings
except ImportError:
    raise Exception("Cannot import settings")
setup_environ(settings)

BROKER_HOST = 'localhost'
BROKER_PORT = 5672
BROKER_USER = 'guest'
BROKER_PASSWORD = 'guest'
BROKER_VHOST = '/'

CONSUMER_QUEUE = 'feed'
CONSUMER_EXCHANGE = 'sample'
CONSUMER_KEY = '#'


def main():
    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                      dest='verbose', help='Enable verbose logging')
    parser.add_option('--host', default=BROKER_HOST, dest='host',
                      help='RabbitMQ host (default: %s)' % BROKER_HOST)
    parser.add_option('--port', default=BROKER_PORT, dest='port',
                      help='RabbitMQ port (default: %s)' % BROKER_PORT, type='int')
    parser.add_option('--user', default=BROKER_USER, dest='user',
                      help='RabbitMQ user (default: %s)' % BROKER_USER)
    parser.add_option('--password', default=BROKER_PASSWORD, dest='password',
                      help='RabbitMQ password (default: %s)' % BROKER_PASSWORD)
    parser.add_option('--vhost', default=BROKER_VHOST, dest='vhost',
                      help='RabbitMQ vhost (default: %s)' % BROKER_VHOST)
    parser.add_option('--queue', default=CONSUMER_QUEUE, dest='queue',
                      help='RabbitMQ queue (default: %s)' % CONSUMER_QUEUE)
    parser.add_option('--exchange', default=CONSUMER_EXCHANGE, dest='exchange',
                      help='RabbitMQ exchange (default: %s)' % CONSUMER_EXCHANGE)
    parser.add_option('--key', default=CONSUMER_KEY, dest='key',
                      help='RabbitMQ key (default: %s)' % CONSUMER_KEY)
    parser.add_option('--callback', default=None, dest='callback',
                      help='Callback function to consume messages')
    parser.add_option('--test', action='store_true', default=False,
                      dest='test', help='Produce a dummy message for testing')
    opts, args = parser.parse_args()

    DEBUG = False
    if opts.verbose:
        DEBUG = True
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.DEBUG if DEBUG else logging.INFO)
    logger = logging.getLogger('dispatcher')

    host =  'amqp://%s:%s@%s:%s' % (opts.user, opts.password, opts.host, opts.port)
    queue = opts.queue
    key = opts.key
    exchange = opts.exchange
    
    client = AMQPClient(hosts=[host])
    client.connect()

    if opts.test:
        client.exchange_declare(exchange=exchange,
                                type='topic')
        client.basic_publish(exchange=exchange,
                             routing_key=key,
                             body= json.dumps({"test": "0123456789"}))
        client.close()
        sys.exit()

    callback = None
    if opts.callback:
        cb = opts.callback.rsplit('.', 1)
        if len(cb) == 2:
            __import__(cb[0])
            cb_module = sys.modules[cb[0]]
            callback = getattr(cb_module, cb[1])

    def handle_message(client, msg):
        logger.debug('%s', msg)
        if callback:
            callback(msg)
        client.basic_ack(msg)

    client.queue_declare(queue=queue)
    client.queue_bind(queue=queue,
                      exchange=exchange,
                      routing_key=key)

    client.basic_consume(queue=queue, callback=handle_message)

    try:
        while True:
            client.basic_wait()
    except KeyboardInterrupt:
        pass
    finally:
        client.close()


if __name__ == '__main__':
    main()
