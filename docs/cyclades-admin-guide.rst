.. _cyclades-admin-guide:

===================
Administrator Guide
===================

This is the cyclades administrator guide.

It contains instructions on how to download, install and configure
the synnefo components necessary to deploy the Compute Service. It also covers
maintenance issues, e.g., upgrades of existing deployments.

The guide assumes you are familiar with all aspects of downloading, installing
and configuring packages for the Linux distribution of your choice.

Overview
--------

This guide covers the following:

Architecture
    Node types needed for a complete deployment of cyclades,
    and their roles. Throughout this guide, `node` refers to a physical machine
    in the deployment.
Installation
    The installation of services and synnefo software components for a working
    deployment of cyclades, either from source packages or the provided
    packages for Debian Squeeze.
Configuration
    Configuration of the various software components comprising an cyclades
    deployment.
Upgrades/Changelogs
    Upgrades of existing deployments of cyclades to newer versions, associated
    Changelogs.

.. _cyclades-architecture:

Architecture
------------

Nodes in an cyclades deployment belong in one of the following types.
For every type, we list the services that execute on corresponding nodes.

.. _DB_NODE:

DB
**

A node [or more than one nodes, if using an HA configuration], running a DB
engine supported by the Django ORM layer. The DB is the single source of
truth for the servicing of API requests by cyclades.

*Services:* PostgreSQL / MySQL

.. _APISERVER_NODE:

APISERVER
*********
A node running the ``api`` application contained in
:ref:`snf-cyclades-app <snf-cyclades-app>`. Any number of
:ref:`APISERVER <APISERVER_NODE>` nodes
can be used, in a load-balancing configuration, without any
special consideration. Access to a common DB ensures consistency.

*Services:* Web server, vncauthproxy


.. _QUEUE_NODE:

QUEUE
*****
A node running the RabbitMQ software, which provides AMQP functionality. More
than one :ref:`QUEUE <QUEUE_NODE>` nodes may be deployed, in an HA
configuration. Such deployments require shared storage, provided e.g., by DRBD.

*Services:* RabbitMQ [rabbitmq-server]


.. _LOGIC_NODE:

LOGIC
*****

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
*****************************
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

.. _WEBAPP_NODE:

Installation
------------

Installation of cyclades is a two step process:

1. install the external services (prerequisites) on which cyclades depends
2. install the synnefo software components associated with cyclades

Prerequisites
*************
.. _cyclades-install-ganeti:

Ganeti installation
```````````````````
Synnefo requires a working Ganeti installation at the backend. Installation
of Ganeti is not covered by this document, please refer to
`ganeti documentation <http://docs.ganeti.org/ganeti/current/html>`_ for all the 
gory details. A successful Ganeti installation concludes with a working 
:ref:`GANETI-MASTER <GANETI_NODES>` and a number of :ref:`GANETI-NODEs <GANETI_NODES>`.

.. _cyclades-install-db:

Database
````````

Database installation is done as part of the
:ref:`snf-webproject <snf-webproject>` component.

.. _cyclades-install-rabbitmq:

RabbitMQ 
````````

RabbitMQ is used as a generic message broker for cyclades. It should be
installed on two seperate :ref:`QUEUE <QUEUE_NODE>` nodes in a high availability
configuration as described here:

    http://www.rabbitmq.com/pacemaker.html

After installation, create a user and set its permissions:

.. code-block:: console

    $ rabbitmqctl add_user <username> <password>
    $ rabbitmqctl set_permissions -p / <username>  "^.*" ".*" ".*"

The values set for the user and password must be mirrored in the
``RABBIT_*`` variables in your settings, as managed by
:ref:`snf-common <snf-common>`.

.. todo:: Document an active-active configuration based on the latest version
   of RabbitMQ.

.. _cyclades-install-vncauthproxy:

vncauthproxy
````````````

To support OOB console access to the VMs over VNC, the vncauthproxy
daemon must be running on every :ref:`APISERVER <APISERVER_NODE>` node.

.. note:: The Debian package for vncauthproxy undertakes all configuration
   automatically.

Download and install the latest vncauthproxy from its own repository,
at `https://code.grnet.gr/git/vncauthproxy`, or a specific commit:

.. code-block:: console

    $ bin/pip install -e git+https://code.grnet.gr/git/vncauthproxy@INSERT_COMMIT_HERE#egg=vncauthproxy

Create ``/var/log/vncauthproxy`` and set its permissions appropriately.

Alternatively, build and install Debian packages.

.. code-block:: console

    $ git checkout debian
    $ dpkg-buildpackage -b -uc -us
    # dpkg -i ../vncauthproxy_1.0-1_all.deb

.. warning::
    **Failure to build the package on the Mac.**

    ``libevent``, a requirement for gevent which in turn is a requirement for
    vncauthproxy is not included in `MacOSX` by default and installing it with
    MacPorts does not lead to a version that can be found by the gevent
    build process. A quick workaround is to execute the following commands::

        $ cd $SYNNEFO
        $ sudo pip install -e git+https://code.grnet.gr/git/vncauthproxy@5a196d8481e171a#egg=vncauthproxy
        <the above fails>
        $ cd build/gevent
        $ sudo python setup.py -I/opt/local/include -L/opt/local/lib build
        $ cd $SYNNEFO
        $ sudo pip install -e git+https://code.grnet.gr/git/vncauthproxy@5a196d8481e171a#egg=vncauthproxy

.. todo:: Mention vncauthproxy bug, snf-vncauthproxy, inability to install using pip
.. todo:: kpap: fix installation commands

.. _cyclades-install-nfdhcpd:

NFDHCPD
```````

Setup Synnefo-specific networking on the Ganeti backend.
This part is deployment-specific and must be customized based on the
specific needs of the system administrators.

A reference installation will use a Synnefo-specific KVM ifup script,
NFDHCPD and pre-provisioned Linux bridges to support public and private
network functionality. For this:

Grab NFDHCPD from its own repository (https://code.grnet.gr/git/nfdhcpd),
install it, modify ``/etc/nfdhcpd/nfdhcpd.conf`` to reflect your network
configuration.

Install a custom KVM ifup script for use by Ganeti, as
``/etc/ganeti/kvm-vif-bridge``, on GANETI-NODEs. A sample implementation is
provided under ``/contrib/ganeti-hooks``. Set ``NFDHCPD_STATE_DIR`` to point
to NFDHCPD's state directory, usually ``/var/lib/nfdhcpd``.

.. todo:: soc: document NFDHCPD installation, settle on KVM ifup script

.. _cyclades-install-snfimage:

snf-image
`````````

Install the :ref:`snf-image <snf-image>` Ganeti OS provider for image
deployment.

For :ref:`cyclades <cyclades>` to be able to launch VMs from specified
Images, you need the snf-image OS Provider installed on *all* Ganeti nodes.

Please see `https://code.grnet.gr/projects/snf-image/wiki`_
for installation instructions and documentation on the design
and implementation of snf-image.

Please see `https://code.grnet.gr/projects/snf-image/files`
for the latest packages.

Images should be stored in ``extdump``, or ``diskdump`` format in a directory
of your choice, configurable as ``IMAGE_DIR`` in 
:file:`/etc/default/snf-image`.

synnefo components
******************

You need to install the appropriate synnefo software components on each node,
depending on its type, see :ref:`Architecture <cyclades-architecture>`.

Most synnefo components have dependencies on additional Python packages.
The dependencies are described inside each package, and are setup
automatically when installing using :command:`pip`, or when installing 
using your system's package manager.

Please see the page of each synnefo software component for specific
installation instructions, where applicable.

Install the following synnefo components:

Nodes of type :ref:`APISERVER <APISERVER_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-webproject <snf-webproject>`,
    :ref:`snf-cyclades-app <snf-cyclades-app>`
Nodes of type :ref:`GANETI-MASTER <GANETI_MASTER>` and :ref:`GANETI-NODE <GANETI_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-cyclades-gtools <snf-cyclades-gtools>`
Nodes of type :ref:`LOGIC <LOGIC_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-webproject <snf-webproject>`,
    :ref:`snf-cyclades-app <snf-cyclades-app>`.

Configuration
-------------

This section targets the configuration of the prerequisites for cyclades,
and the configuration of the associated synnefo software components.

synnefo components
******************

cyclades uses :ref:`snf-common <snf-common>` for settings.
Please refer to the configuration sections of
:ref:`snf-webproject <snf-webproject>`,
:ref:`snf-cyclades-app <snf-cyclades-app>`,
:ref:`snf-cyclades-gtools <snf-cyclades-gtools>` for more
information on their configuration.

Ganeti
``````

Set ``GANETI_NODES``, ``GANETI_MASTER_IP``, ``GANETI_CLUSTER_INFO`` based on
your :ref:`Ganeti installation <cyclades-install-ganeti>` and change the
`BACKEND_PREFIX_ID`` setting, using an custom ``PREFIX_ID``.

Database
````````

Once all components are installed and configured,
initialize the Django DB:

.. code-block:: console

   $ snf-manage syncdb
   $ snf-manage migrate

and load fixtures ``{users, flavors, images}``, 
which make the API usable by end users by defining a sample set of users, 
hardware configurations (flavors) and OS images:

.. code-block:: console

   $ snf-manage loaddata /path/to/users.json
   $ snf-manage loaddata flavors
   $ snf-manage loaddata images

.. warning:: 
    Be sure to load a custom users.json and select a unique token 
    for each of the initial and any other users defined in this file. 
    **DO NOT LEAVE THE SAMPLE AUTHENTICATION TOKENS** enabled in deployed
    configurations.

sample users.json file:

.. literalinclude:: ../../synnefo/db/fixtures/users.json

`download <../_static/users.json>`_

RabbitMQ
````````

Change ``RABBIT_*`` settings to match your :ref:`RabbitMQ setup
<cyclades-install-rabbitmq>`.

.. include:: ../../Changelog
