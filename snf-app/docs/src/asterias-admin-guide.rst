.. _snf-asterias-admin-guide:

===================
Administrator Guide
===================

This is the asterias administrator guide.

It contains instructions on how to download, install and configure
the synnefo components necessary to deploy the Compute Service. It also covers
maintenance issues, e.g., upgrades of existing deployments.

The guide assumes you are familiar with all aspects of downloading, installing
and configuring packages for the Linux distribution of your choice.

Overview
--------

This guide covers the following:

Architecture
    Node types needed for a complete deployment of asterias,
    and their roles. Throughout this guide, `node` refers to a physical machine
    in the deployment.
Installation
    The installation of services and synnefo software components for a working
    deployment of asterias, either from source packages or the provided
    packages for Debian Squeeze.
Configuration
    Configuration of the various software components comprising an asterias
    deployment.
Upgrades
Changelogs

.. todo:: describe prerequisites -- e.g., Debian
.. todo:: describe setup of nginx, flup, synnefo packages, etc.

.. _snf-asterias-architecture:

Architecture
------------

Nodes in an asterias deployment belong in one of the following types.
For every type, we list the services that execute on corresponding nodes.

.. _DB_NODE:

DB
**

A node [or more than one nodes, if using an HA configuration], running a DB
engine supported by the Django ORM layer. The DB is the single source of
truth for the servicing of API requests by asterias.

*Services:* PostgreSQL / MySQL

.. _APISERVER_NODE:

APISERVER
*********
A node running the ``api`` application contained in
:ref:`snf-asterias-app <snf-asterias-app>`. Any number of
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
        * properly configured :ref:`NFDHCPD <nfdhcpd-setup>`

.. _WEBAPP_NODE:

Installation
------------

Installation of asterias is a two step process:

1. install the external services (prerequisites) on which asterias depends
2. install the synnefo software components associated with asterias

Prerequisites
*************
.. _ganeti-setup:

1. Ganeti installation
``````````````````````
Synnefo requires a working Ganeti installation at the backend. Installation
of Ganeti is not covered by this document, please refer to
`ganeti documentation <http://docs.ganeti.org/ganeti/current/html>`_ for all the 
gory details. A successful Ganeti installation concludes with a working 
:ref:`GANETI-MASTER <GANETI_NODES>` and a number of :ref:`GANETI-NODEs <GANETI_NODES>`.

2. Database
```````````

SQLite
~~~~~~
Most self-respecting systems have ``sqlite`` installed by default.

MySQL
~~~~~
MySQL must be installed first:

.. code-block:: console

    # apt-get install libmysqlclient-dev

if you are using MacPorts:

.. code-block:: console

    $ sudo port install mysql5

.. note::

    On MacOSX with Mysql install from MacPorts the above command will
    fail complaining that it cannot find the mysql_config command. Do
    the following and restart the installation:

    .. code-block:: console

       $ echo "mysql_config = /opt/local/bin/mysql_config5" >> ./build/MySQL-python/site.cfg

Configure a MySQL db/account for the Django project:

.. code-block:: console

    $ mysql -u root -p;

.. code-block:: mysql

    CREATE DATABASE <database name>;
    SHOW DATABASES;
    GRANT ALL ON <database name>.* TO <db username> IDENTIFIED BY '<db password>';

.. warning::
        MySQL *must* be set in ``READ-COMMITED`` mode, e.g. by setting:

   .. code-block:: ini
   
      transaction-isolation = READ-COMMITTED
               
   in the ``[mysqld]`` section of :file:`/etc/mysql/my.cnf`.

   Alternatively, make sure the following code fragment stays enabled
   in :file:`/etc/synnefo/10-database.conf` file:
       
   .. code-block:: python
   
       if DATABASES['default']['ENGINE'].endswith('mysql'):
           DATABASES['default']['OPTIONS'] = {
                   'init_command': 'SET storage_engine=INNODB; ' +
                       'SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED',
           }
   
PostgreSQL
~~~~~~~~~~

You need to install the PostgreSQL binaries, e.g., for Debian:

.. code-block:: console
	     
    # apt-get install postgresql-8.4 libpq-dev

or ir you are using MacPorts:

.. code-block:: console

    $ sudo port install postgresql84

To configure a postgres db/account for synnefo,

*  Become the postgres user, connect to PostgreSQL:

.. code-block:: console

       $ sudo su - postgres
       $ psql
	
* Run the following commands:

.. code-block:: sql

	   DROP DATABASE <database name>;
	   DROP USER <db username>;
	   CREATE USER <db username> WITH PASSWORD '<db password>';
	   CREATE DATABASE <database name>;
	   GRANT ALL PRIVILEGES ON DATABASE <database name> TO <db username>;
	   ALTER DATABASE <database name> OWNER TO <db username>;
	   ALTER USER <db username> CREATEDB;
       
.. note:: 
   The last line enables the newly created user to create own databases. This
   is needed for Django to create and drop the ``test_synnefo`` database for
   unit testing.

3. RabbitMQ 
```````````

RabbitMQ is used as a generic message broker for asterias. It should be
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

4. vncauthproxy
```````````````

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

.. _nfdhcpd-setup:

5. NFDHCPD
``````````

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

.. _rabbitmq-setup:

6. snf-image
````````````

Install the :ref:`snf-image <snf-image>` Ganeti OS provider for image
deployment.

For :ref:`asterias <snf-asterias>` to be able to launch VMs from specified
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
depending on its type, see :ref:`Architecture <snf-asterias-architecture>`.

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
    :ref:`snf-asterias-app <snf-asterias-app>`
Nodes of type :ref:`GANETI-MASTER <GANETI_MASTER>` and :ref:`GANETI-NODE <GANETI_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-asterias-ganeti-tools <snf-asterias-ganeti-tools>`
Nodes of type :ref:`LOGIC <LOGIC_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-webproject <snf-webproject>`,
    :ref:`snf-asterias-app <snf-asterias-app>`.

Configuration
-------------

asterias uses :ref:`snf-common <snf-common>` for settings.
Please refer to the configuration sections of
:ref:`snf-webproject <snf-webproject>`,
:ref:`snf-asterias-app <snf-asterias-app>`,
:ref:`snf-asterias-ganeti-tools <snf-asterias-ganeti-tools>` for more
information on their configuration.
