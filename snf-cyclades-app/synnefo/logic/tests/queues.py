# Copyright (C) 2010-2016 GRNET S.A.
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

from django.test import TestCase

from synnefo.logic import queues

class QueuesTest(TestCase):
    queue = 'queue'
    exchange = 'exchange'
    hostname = 'hostname'
    pid = 1

    def test_convert_queue_to_dead(self):
        converted = queues.convert_queue_to_dead(self.queue)

        self.assertEqual(self.queue + '-dl', converted)

    def test_convert_exchange_to_dead(self):
        converted = queues.convert_exchange_to_dead(self.exchange)

        self.assertEqual(self.exchange + '-dl', converted)

    def test_get_dispatcher_request_queue(self):
        expected = "snf:dispatcher:{0}:{1}".format(self.hostname, self.pid)
        converted = queues.get_dispatcher_request_queue(
            self.hostname,
            self.pid
        )

        self.assertEqual(expected, converted)

    def test_get_dispatcher_heartbeat_queue(self):
        expected = "snf:dispatcher:heartbeat:{0}:{1}".format(
            self.hostname,
            self.pid
        )
        converted = queues.get_dispatcher_heartbeat_queue(
            self.hostname,
            self.pid
        )

        self.assertEqual(expected, converted)
