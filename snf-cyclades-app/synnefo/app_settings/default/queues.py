# -*- coding: utf-8 -*-
#
# Queues, exchanges and bindings for AMQP
###########################################

# List of RabbitMQ endpoints
AMQP_HOSTS = ["amqp://username:password@host:port"]
# AMQP Backend Client. Currently only puka
AMQP_BACKEND = 'puka'

EXCHANGE_GANETI = "ganeti"  # Messages from Ganeti
EXCHANGE_CRON = "cron"      # Messages from periodically triggered tasks
EXCHANGE_API = "api"        # Messages from the REST API
EXCHANGES = (EXCHANGE_GANETI, EXCHANGE_CRON, EXCHANGE_API)
