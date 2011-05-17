import time
from amqplib import client_0_8 as amqp
from django.conf import settings

conn = None

class AMQPConnection:

    def connect(self):
        while conn == None:
            try:
                conn = amqp.Connection(host=settings.RABBIT_HOST,
                               userid=settings.RABBIT_USERNAME,
                               password=settings.RABBIT_PASSWORD,
                               virtual_host=settings.RABBIT_VHOST)
            except socket.error:
                time.sleep(1)

    

