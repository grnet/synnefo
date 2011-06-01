import time
import socket
from amqplib import client_0_8 as amqp
from django.conf import settings

_conn = None
_chan = None

def _connect():
    global _conn, _chan
    while _conn == None:
        try:
            _conn = amqp.Connection(host=settings.RABBIT_HOST,
                                   userid=settings.RABBIT_USERNAME,
                                   password=settings.RABBIT_PASSWORD,
                                   virtual_host=settings.RABBIT_VHOST)
        except socket.error:
            time.sleep(1)
    _chan = _conn.channel()


def send(payload, exchange, key):
    """
        Send payload to the specified exchange using the provided routing key
    """
    global _conn, _chan

    if payload is None:
        raise AMQPError("Message is empty")

    if exchange is None:
        raise AMQPError("Unknown exchange")

    if key is None:
        raise AMQPError("Unknown routing key")

    msg = amqp.Message(payload)
    msg.properties["delivery_mode"] = 2  # Persistent

    while True:
        try:
           _chan.basic_publish(msg,
                               exchange=exchange,
                               routing_key=key)
           return
        except socket.error:
           #logger.exception("Server went away, reconnecting...")
           _connect()
        except Exception as e:
            if _conn is None:
               _connect()
            else:
                #self.logger.exception("Caught unexpected exception (msg: %s)", msg)
               raise AMQPError("Error sending message to exchange %s with key %s. Payload: %s. Error was: %s",
               (exchange, key, payload, e.message))

def __init__():
    _connect()


class AMQPError(Exception):
    def __init__(self, msg):
        self.message = msg
