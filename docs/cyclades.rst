.. _cyclades:

Compute and Network Service (cyclades)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Cyclades is the the synnefo Compute and Network Service.

It implements OpenStack Compute API v1.1 + synnefo extensions.

.. todo:: list synnefo components needed by cyclades

.. _cyclades-architecture:

Cyclades Architecture
=====================

.. todo:: document the overall cyclades architecture

Nodes in an cyclades deployment belong in one of the following types.
For every type, we list the services that execute on corresponding nodes.
Throughout this guide, `node` refers to a physical machine in the deployment.

.. _DB_NODE:

DB
--

A node [or more than one nodes, if using an HA configuration], running a DB
engine supported by the Django ORM layer. The DB is the single source of
truth for the servicing of API requests by cyclades.

*Services:* PostgreSQL / MySQL

.. _APISERVER_NODE:

APISERVER
---------

A node running the ``api`` application contained in
:ref:`snf-cyclades-app <snf-cyclades-app>`. Any number of
:ref:`APISERVER <APISERVER_NODE>` nodes
can be used, in a load-balancing configuration, without any
special consideration. Access to a common DB ensures consistency.

*Services:* Web server, vncauthproxy


.. _QUEUE_NODE:

QUEUE
-----

A node running the RabbitMQ software, which provides AMQP functionality. More
than one :ref:`QUEUE <QUEUE_NODE>` nodes may be deployed, in an HA
configuration. Such deployments require shared storage, provided e.g., by DRBD.

*Services:* RabbitMQ [rabbitmq-server]


.. _LOGIC_NODE:

LOGIC
-----

A node running the business logic of synnefo, in Django. It dequeues
messages from QUEUE nodes, and provides the context in which business logic
functions run. It uses Django ORM to connect to the common DB and update the
state of the system, based on notifications received from the rest of the
infrastructure, over AMQP.

*Services:* the synnefo logic dispatcher, ``snf-dispatcher``


.. _GANETI_NODES:
.. _GANETI_MASTER:
.. _GANETI_NODE:

GANETI-MASTER and GANETI-NODE
-----------------------------

A single GANETI-MASTER and a large number of GANETI-NODEs constitute the
Ganeti backend for synnefo, which undertakes all VM management functions.
Any APISERVER can issue commands to the GANETI-MASTER, over RAPI, to effect
changes in the state of the VMs. The GANETI-MASTER runs the Ganeti request
queue.

*Services:*
    * only on :ref:`GANETI-MASTER <GANETI_MASTER>`:
        * the synnefo Ganeti monitoring daemon, ``snf-ganeti-eventd``
        * the synnefo Ganeti hook, ``ganeti/snf-ganeti-hook.py``.
    * on every :ref:`GANETI-NODE <GANETI_NODE>`:
        * a deployment-specific KVM ifup script
        * properly configured :ref:`NFDHCPD <cyclades-nfdhcpd-setup>`


..   src/design
..   src/dev
..   src/user
..   src/api

..   src/install
..   src/configuration
..   src/deployment
..   src/admin
..   src/admin_tools
..   src/develop
..   src/api
..   src/plankton
..   src/storage
..   src/upgrade
..   src/changelog

Indices and tables
==================


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
