.. _deployment:

Administrator Guide
===================

This is the snf-compute administrator's guide.

It contains instructions on how to download, install and configure
synnefo components. It also covers maintenance issues, e.g.,
upgrades of existing synnefo deployments.

The guide assumes you are familiar with all aspects of downloading, installing
and configuring packages for the Linux distribution of your choice.

Overview
--------

This guide covers the following:
synnefo architecture
    The node types needed for a complete synnefo deployment, and their roles.
    Throughout this guide, `node` refers to a physical machine in the
    deployment.
synnefo packages
installation
configuration
upgrades
changelogs

.. todo:: describe prerequisites -- e.g., Debian
.. todo:: describe setup of nginx, flup, synnefo packages, etc.

synnefo architecture
--------------------

Nodes in a synnefo deployment belong in one of the following types.
For every type, we list the services that execute on corresponding nodes.

.. _DB_NODE:

DB
**
A node [or more than one nodes, if using an HA configuration], running a DB
engine supported by the Django ORM layer. The DB is the single source of
truth for the servicing of API requests by synnefo.

_Services:_ PostgreSQL / MySQL

.. _APISERVER_NODE:

APISERVER
*********
A node running the implementation of the OpenStack API, in Django. Any number
of APISERVERs can be used, in a load-balancing configuration, without any
special consideration. Access to a common DB ensures consistency.
_Services:_ Web server, vncauthproxy


.. _QUEUE_NODE:

QUEUE
*****
A node running the RabbitMQ software, which provides AMQP functionality. More
than one QUEUE nodes may be deployed, in an HA configuration. Such
deployments require shared storage, provided e.g., by DRBD.
_Services:_ RabbitMQ [rabbitmq-server]


.. _LOGIC_NODE:

LOGIC
*****

A node running the business logic of synnefo, in Django. It dequeues
messages from QUEUE nodes, and provides the context in which business logic
functions run. It uses Django ORM to connect to the common DB and update the
state of the system, based on notifications received from the rest of the
infrastructure, over AMQP.
_Services:_ the synnefo logic dispatcher, ``snf-dispatcher``


.. _GANETI_NODES:
.. _GANETI_MASTER:
.. _GANETI_NODE:
  
GANETI-MASTER and GANETI-NODE
*****************************
A single GANETI-MASTER and a large number of GANETI-NODEs constitute the
Ganeti backend for synnefo, which undertakes all VM management functions.
Any APISERVER can issue commands to the GANETI-MASTER, over RAPI, to effect
changes in the state of the VMs. The GANETI-MASTER runs the Ganeti request
queue.

_Services:_
    * only on :ref:`GANETI-MASTER <GANETI_MASTER>`:
        * the synnefo Ganeti monitoring daemon, ``snf-ganeti-eventd``
        * the synnefo Ganeti hook, ``ganeti/snf-ganeti-hook.py``.
    * on every :ref:`GANETI-NODE <GANETI_NODE>`:
        * a deployment-specific KVM ifup script
        * properly configured :ref:`NFDHCPD <nfdhcpd-setup>`

.. _WEBAPP_NODE:

WEBAPP
******
A WEBAPP node runs the :ref:`snf-app <snf-app>` web application bundled within
the synnefo package.


Installation
------------

Depending on the type of the node, you need to install the following synnefo
components:

Nodes of type :ref:`APISERVER <APISERVER_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-webproject <snf-webproject>`,
    :ref:`snf-app <snf-app>`
Nodes of type :ref:`GANETI-MASTER <GANETI_MASTER>` and :ref:`GANETI-NODE <GANETI_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-ganeti-tools <snf-ganeti-tools>`
Nodes of type :ref:`LOGIC <LOGIC>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-webproject <snf-webproject>`,
    :ref:`snf-app <snf-app>`.

.. todo:: describe prerequisites -- e.g., Debian

Configuration
-------------

The Compute Service uses :ref:`snf-common <snf-common>` for settings.


Web admin
`````````
synnefo web administration interface. Allows administrator users to manage the
synnefo application via web interface.

Web application
```````````````
Web interface which allows users to create/configure/manage their virtual
machines.

.. _dispatcher-deploy:

Dispatcher
----------

The logic dispatcher is part of the synnefo Django project and must run
on :ref:`LOGIC <LOGIC_NODE>` nodes.

The dispatcher retrieves messages from the queue and calls the appropriate
handler function as defined in the queue configuration in ``/etc/synnefo/*.conf``
files.

The default configuration should work directly without any modifications.

For the time being The dispatcher must be run by hand::

  $ snf-dispatcher

The dispatcher should run in at least 2 instances to ensure high
(actually, increased) availability.


.. _webapp-deploy:

Web application deployment
--------------------------

.. _static-files:

Static files
************

* Choose an appropriate path (e.g. ``/var/lib/synnefo/static/``) from which
  your web server will serve all static files (js/css) required by the synnefo
  web frontend to run.
* Change the ``MEDIA_ROOT`` value in your settings to point to that directory.
* Run the following command::

    $ snf-manage link_static

  the command will create symlinks of the appropriate static files inside the
  chosen directory.

.. todo:: describe an ``snf-manage copy_static`` command.

Using Apache
************

.. todo:: document apache configuration

Using nginx
***********

This section describes a sample nginx configuration which uses FastCGI
to relay requests to synnefo. Use a distribution-specific mechanism
(e.g., APT) to install nginx, then activate the following nginx configuration
file by placing it under ``/etc/nginx/sites-available`` and symlinking
under ``/etc/nginx/sites-enabled``:

.. literalinclude:: ../_static/synnefo.nginx.conf

`download <../_static/synnefo.nginx.conf>`_

then run the FastCGI server to receive incoming requests from nginx.
This requires installation of package flup, e.g. with::
    # apt-get install flup
    $ snf-manage runfcgi host=127.0.0.1 port=8015


Console scripts
---------------

snf-manage
**************

snf-dispatcher
******************

snf-admin
*************

snf-cloud
*************

snf-burnin
**************
