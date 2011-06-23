import json

from django.core.mail import send_mail
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
    import logging
    logger = logging.getLogger("synnefo.logic")
    attempts = 0

    while attempts < 3:
        try:
            send_mail(subject, body, sender, [recipient])
            return
        except Exception as e:
            logger.warn("Error sending email: ", e)
        finally:
            attempts += 1
    logger.warn("Failed all %d attempts to send email, aborting", attempts)

