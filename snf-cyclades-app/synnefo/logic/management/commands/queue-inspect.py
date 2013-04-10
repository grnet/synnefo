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

import pprint

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from synnefo.lib.amqp import AMQPClient


class Command(BaseCommand):
    args = "<queue name>"
    help = "Inspect the messages of a queue. Close all other clients in "\
           "order to be able to inspect unacknowledged messages."

    option_list = BaseCommand.option_list + (
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

        pp = pprint.PrettyPrinter(indent=4, width=4)

        more_msgs = True
        counter = 0
        sep = '-' * 80
        while more_msgs:
            msg = client.basic_get(queue=queue)
            if msg:
                counter += 1
                print sep
                print 'Message %d:' % counter
                print sep
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
