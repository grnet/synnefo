# -*- coding: utf-8 -*-
#
# Queues, exchanges and bindings for AMQP
###########################################

# List of RabbitMQ endpoints
AMQP_HOSTS = ["amqp://username:password@host:port"]
# AMQP Backend Client. Currently only puka
AMQP_BACKEND = 'puka'

EXCHANGE_GANETI = "ganeti"  # Messages from Ganeti
