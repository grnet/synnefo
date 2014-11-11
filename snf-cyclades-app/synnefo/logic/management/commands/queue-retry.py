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
from optparse import make_option

from synnefo.lib.amqp import AMQPClient
from snf_django.management.commands import SynnefoCommand

from synnefo.logic import queues

import json
import logging
log = logging.getLogger("")


class Command(SynnefoCommand):
    help = "Resend messages from dead letter queues to original exchange"""

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--keep-zombies',
            action='store_true',
            dest='keep_zombies',
            default=False,
            help="Do not remove messages that died more than one times"),
    )

    def handle(self, *args, **options):
        verbose = (options["verbosity"] == "2")
        self.keep_zombies = options["keep_zombies"]
        log_level = logging.DEBUG if verbose else logging.WARNING
        log.setLevel(log_level)

        client = AMQPClient(confirms=False)
        client.connect()

        self.client = client

        for queue in queues.QUEUES:
            dead_queue = queues.convert_queue_to_dead(queue)
            while 1:
                message = client.basic_get(dead_queue)
                if not message:
                    break
                log.debug("Received message %s", message)
                self.handle_message(message)
        client.close()
        return 0

    def handle_message(self, message):
        try:
            body = message['body']
        except KeyError:
            log.warning("Received message without body: %s", message)
            return

        try:
            body = json.loads(body)
        except ValueError:
            log.error("Removed malformed message with body %s", body)
            self.client.basic_nack(message)
            return

        if "from-dead-letter" in message['headers']:
            if not self.keep_zombies:
                log.info("Removed message that died twice %s", body)
                self.client.basic_nack(message)
                return

        try:
            headers = message['headers']
            death = headers['x-death'][0]
        except KeyError:
            log.warning("Received message without death section %s."
                        "Removing..",
                        message)
            self.client.basic_nack(message)

        # Get Routing Info
        exchange = death['exchange']
        routing_key = death['routing-keys'][0]

        # Add after Death
        body = json.dumps(body)

        self.client.basic_publish(exchange, routing_key, body,
                                  headers={"from-dead-letter": True})
        self.client.basic_ack(message)
