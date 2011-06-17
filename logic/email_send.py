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

from smtplib import SMTP
from email.mime import text
from email.header import Header
from email.utils import parseaddr, formataddr

from django.conf import settings
import amqp_connection


def send_async(frm = settings.SYSTEM_EMAIL_ADDR,
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

    routekey = "logic.email.outgoing"
    amqp_connection.send(json.dumps(msg), settings.EXCHANGE_API, routekey)


def send (sender = settings.SYSTEM_EMAIL_ADDR,
          recipient = None, subject = None, body = None):
    """
        Connect to the email server configured in settings.py
        and send the email.

        All arguments should be Unicode strings (plain ASCII works as well).

        Only the real name part of sender and recipient addresses may contain
        non-ASCII characters.

        The charset of the email will be the first one out of US-ASCII, ISO-8859-1
        and UTF-8 that can represent all the characters occurring in the email.
        
        This method does not perform any error checking and does
        not guarantee delivery
    """

    # Header class is smart enough to try US-ASCII, then the charset we
    # provide, then fall back to UTF-8.
    header_charset = 'ISO-8859-7'

    # We must choose the body charset manually
    for body_charset in 'US-ASCII', 'ISO-8859-7', 'UTF-8':
        try:
            body.encode(body_charset)
        except UnicodeError:
            pass
        else:
            break

    # Split real name (which is optional) and email address parts
    sender_name, sender_addr = parseaddr(sender)
    recipient_name, recipient_addr = parseaddr(recipient)

    # We must always pass Unicode strings to Header, otherwise it will
    # use RFC 2047 encoding even on plain ASCII strings.
    sender_name = str(Header(unicode(sender_name), header_charset))
    recipient_name = str(Header(unicode(recipient_name), header_charset))

    # Make sure email addresses do not contain non-ASCII characters
    sender_addr = sender_addr.encode('ascii')
    recipient_addr = recipient_addr.encode('ascii')

    # Create the message ('plain' stands for Content-Type: text/plain)
    msg = text.MIMEText(body.encode(body_charset), 'plain', body_charset)
    msg['From'] = formataddr((sender_name, sender_addr))
    msg['To'] = formataddr((recipient_name, recipient_addr))
    msg['Subject'] = Header(unicode(subject), header_charset)

    s = SMTP(host=settings.SMTP_SERVER)
    s.sendmail(sender, recipient, msg.as_string())
    s.quit()
