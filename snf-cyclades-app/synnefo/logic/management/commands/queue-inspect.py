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

import pprint

from optparse import make_option
from django.core.management.base import CommandError

from synnefo.lib.amqp import AMQPClient
from snf_django.management.commands import SynnefoCommand


class Command(SynnefoCommand):
    args = "<queue_name>"
    help = "Inspect the messages of a queue. Close all other clients in "\
           "order to be able to inspect unacknowledged messages."

    option_list = SynnefoCommand.option_list + (
        make_option('--no-requeue', action='store_false', dest='requeue',
                    default=True, help="Do not requeue the messages"),
        make_option('-i', '--interactive', action='store_true', default=False,
                    dest='interactive', help="Interactive mode")
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a queue")

        queue = args[0]
        interactive = options['interactive']
        requeue = options['requeue']

        client = AMQPClient()
        client.connect()

        pp = pprint.PrettyPrinter(indent=4, width=4, stream=self.stdout)

        more_msgs = True
        counter = 0
        sep = '-' * 80
        while more_msgs:
            msg = client.basic_get(queue=queue)
            if msg:
                counter += 1
                self.stderr.write(sep + "\n")
                self.stderr.write('Message %d:\n' % counter)
                self.stderr.write(sep + "\n")
                pp.pprint(msg)
                if not requeue or interactive:
                    if interactive and not get_user_confirmation():
                        continue
                    # Acknowledging the message will remove it from the queue
                    client.basic_ack(msg)
            else:
                more_msgs = False


def get_user_confirmation():
    ans = raw_input("Do you want to delete this message (N/y):")

    if not ans:
        return False
    if ans not in ['Y', 'y']:
        return False
    return True
