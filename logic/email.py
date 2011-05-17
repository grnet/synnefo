import smtplib
import json
import time
import socket
from email.mime.text import MIMEText

from django.conf import settings
from amqplib import client_0_8 as amqp

def send_async(frm, to, subject, body):
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

    msg = amqp.Message(json.dumps(msg))
    msg.properties["delivery_mode"] = 2  # Persistent

    conn = None
    while conn == None:
        try:
            conn = amqp.Connection(host=settings.RABBIT_HOST,
                                   userid=settings.RABBIT_USERNAME,
                                   password=settings.RABBIT_PASSWORD,
                                   virtual_host=settings.RABBIT_VHOST)
        except socket.error:
            time.sleep(1)

    chan = conn.channel()
    chan.basic_publish(msg,exchange=settings.EXCHANGE_EMAIL, routing_key=routekey)


def send (frm, to, subject, body):
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
