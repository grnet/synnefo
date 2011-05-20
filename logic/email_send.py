import json
import smtplib
from email.mime.text import MIMEText

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


def send (frm = settings.SYSTEM_EMAIL_ADDR,
          to = None, subject = None, body = None):
    """
        Connect to the email server configured in settings.py
        and send the email.

        This method does not perform any error checking and does
        not guarantee delivery
    """

    msg = MIMEText(body, _charset="utf-8")
    msg['Subject'] = subject
    msg['From'] = frm
    msg['To'] = to

    s = smtplib.SMTP(host=settings.SMTP_SERVER)
    s.sendmail(frm, [to], msg.as_string())
    s.quit()
