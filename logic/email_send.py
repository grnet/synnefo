# Copyright 2011 GRNET S.A. All rights reserved.
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

# Methods for sending email

import json

from django.core.mail import send_mail
from django.conf import settings
import amqp_connection

from synnefo.logic import log

_logger = log.get_logger("synnefo.logic")
_prefix = settings.BACKEND_PREFIX_ID.split('-')[0]

def send_async(frm = settings.DEFAULT_FROM_EMAIL,
               to = None, subject = None, body = None):
    """
        Queue a message to be sent sometime later
        by a worker process.
    """

    msg = dict()
    msg['frm'] = frm
    msg['to'] = to
    msg['subject'] = subject
    msg['body'] = body

    routekey = "logic.%s.email.outgoing" % _prefix
    amqp_connection.send(json.dumps(msg), settings.EXCHANGE_API, routekey)


def send (sender = settings.DEFAULT_FROM_EMAIL,
          recipient = None, subject = None, body = None):

    attempts = 0

    while attempts < 3:
        try:
            send_mail(subject, body, sender, [recipient])
            return True
        except Exception as e:
            _logger.exception("Error sending email")
        finally:
            attempts += 1

    _logger.warn("Failed all %d attempts to send email, aborting", attempts)
    return False

