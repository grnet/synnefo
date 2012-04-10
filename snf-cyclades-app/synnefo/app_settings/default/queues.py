# -*- coding: utf-8 -*-
#
# Queues, exchanges and bindings for AMQP
###########################################

# Rabbit work queue endpoint
RABBIT_HOST = "10.0.0.1:5672"
RABBIT_USERNAME = "username"
RABBIT_PASSWORD = "password"
RABBIT_VHOST = "/"
AMQP_HOSTS=["amqp://username:password@host:port"]

EXCHANGE_GANETI = "ganeti"  # Messages from Ganeti
EXCHANGE_CRON = "cron"      # Messages from periodically triggered tasks
EXCHANGE_API = "api"        # Messages from the REST API
EXCHANGES = (EXCHANGE_GANETI, EXCHANGE_CRON, EXCHANGE_API)
