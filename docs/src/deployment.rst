.. _deployment:

Deployment
==========

Node types
----------

Nodes in a Synnefo deployment belong in one of the following types:


.. _DB_NODE:

DB
**
A node [or more than one nodes, if using an HA configuration], running a DB
engine supported by the Django ORM layer. The DB is the single source of
truth for the servicing of API requests by Synnefo.
Services: PostgreSQL / MySQL


.. _APISERVER_NODE:

APISERVER
*********
A node running the implementation of the OpenStack API, in Django. Any number
of APISERVERs can be used, in a load-balancing configuration, without any
special consideration. Access to a common DB ensures consistency.
Services: Web server, vncauthproxy


.. _QUEUE_NODE:

QUEUE
*****
A node running the RabbitMQ software, which provides AMQP functionality. More
than one QUEUE nodes may be deployed, in an HA configuration. Such
deployments require shared storage, provided e.g., by DRBD.
Services: RabbitMQ [rabbitmq-server]


.. _LOGIC_NODE:

LOGIC
*****
A node running the business logic of Synnefo, in Django. It dequeues
messages from QUEUE nodes, and provides the context in which business logic
functions run. It uses Django ORM to connect to the common DB and update the
state of the system, based on notifications received from the rest of the
infrastructure, over AMQP.
Services: the Synnefo logic dispatcher [``synnefo-dispatcher``]


.. _GANETI_NODES:

GANETI-MASTER and GANETI-NODE
*****************************
A single GANETI-MASTER and a large number of GANETI-NODEs constitute the
Ganeti backend for Synnefo, which undertakes all VM management functions.
Any APISERVER can issue commands to the GANETI-MASTER, over RAPI, to effect
changes in the state of the VMs. The GANETI-MASTER runs the Ganeti request
queue.

Services:
 only on GANETI-MASTER:
   the Synnefo Ganeti monitoring daemon [/ganeti/snf-ganeti-eventd]
   the Synnefo Ganeti hook [/ganeti/snf-ganeti-hook.py].
 on each GANETI_NODE:
   a deployment-specific KVM ifup script
   properly configured :ref:`NFDHCPD <nfdhcpd-setup>`


.. _WEBAPP_NODE:

WEBAPP
******
Synnefo WEBAPP node is the server that runs the web application contained within
the synnefo package. At the current state Synnefo provides two web frontends.


.. _webapp-deploy:

Web application deployment
--------------------------

Using Apache
************

.. todo:: document apache configuration

Using nginx
***********

.. todo:: document nginx configuration

Serving static files
********************

.. todo:: document serving static files instructions

