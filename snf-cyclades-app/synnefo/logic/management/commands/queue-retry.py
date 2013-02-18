# Copyright 2011-2012 GRNET S.A. All rights reserved.
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
#
from django.core.management.base import BaseCommand
from optparse import make_option

from synnefo.lib.amqp import AMQPClient

from synnefo.logic import queues

import json
import logging
log = logging.getLogger("")


class Command(BaseCommand):
    help = "Resend messages from dead letter queues to original exchange"""

    option_list = BaseCommand.option_list + (
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
