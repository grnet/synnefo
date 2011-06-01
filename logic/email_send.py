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
