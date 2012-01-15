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

WEBAPP
******
A WEBAPP node runs the web application provided by the synnefo component
:ref:`snf-asterias-app <snf-asterias-app>`.

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

    $ sudo apt-get install libmysqlclient-dev

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
	     
    $ sudo apt-get install postgresql-8.4 libpq-dev

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

Images should be stored under extdump format in a directory
of your choice, configurable as ``IMAGE_DIR`` in 
:file:`/etc/default/snf-image`.

synnefo components
******************

You need to install the following synnefo components on each node,
depending on its type. Please see the page of each synnefo software
component for specific installation instructions, where applicable.

Nodes of type :ref:`APISERVER <APISERVER_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-webproject <snf-webproject>`,
    :ref:`snf-asterias-app <snf-asterias-app>`
Nodes of type :ref:`GANETI-MASTER <GANETI_MASTER>` and :ref:`GANETI-NODE <GANETI_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-ganeti-tools <snf-ganeti-tools>`
Nodes of type :ref:`LOGIC <LOGIC_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-webproject <snf-webproject>`,
    :ref:`snf-asterias-app <snf-asterias-app>`.

.. todo:: describe prerequisites -- e.g., Debian

Configuration
-------------

asterias uses :ref:`snf-common <snf-common>` for settings.

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
handler function as defined in the queue configuration in :file:`/etc/synnefo/*.conf`
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

* Choose an appropriate path (e.g. :file:`/var/lib/synnefo/static/`) from which
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



.. _installation:


.. _database-setup:



Installing depedencies
**********************

Synnefo is written in Python 2.6 requires the some additional python packages 
to run properly.

The easiest method for installation of the Django project is to setup a
working environment through virtualenv. Alternatively, you can use your
system's package manager to install the dependencies (e.g. Macports has them
all).

You can install these packages either using `pip` python package manager::
    
    $ pip install <pypi-package-name>==<version>

or using the requirements.pip file that exists in Synnefo package repository::

    $ pip install -r requirements.pip

or Debian's `apt-get`::

    $ apt-get install <debian-package-name>


Required packages
`````````````````

.. todo::
    Confirm debian package names

=======================     ===================         ==========
PyPi package name           Debian package name         version   
=======================     ===================         ==========
django                      python-django               1.2.4      
simplejson                  python-simplejson           2.1.3
pycurl                      python-pycurl               7.19.0
python-dateutil             python-dateutil             1.4.1
IPy                         python-ipy                  0.75
south                       python-django-south         0.7.1
amqplib                     python-amqplib              0.6.1
lockfile                    python-lockfile             0.8
python-daemon               python-daemon               1.5.5
python-prctl                python-prctl                1.3.0
=======================     ===================         ==========

.. note::
    On Snow Leopard and linux (64-bit), you have to set the following
    environment variable for pip to compile the dependencies correctly::

        $ export ARCHFLAGS="-arch x86_64"

.. note::
    On Ubuntu/Debian, a few more packages must be installed before installing the
    prerequisite Python libraries::

        $ sudo aptitude install libcurl3-gnutls libcurl3-gnutls-dev uuid-dev

.. note::
    Depending on the permissions of your system’s Python, you might need to be the 
    root user to install those packages system-wide


Database driver
```````````````

Depending on the database software you choose to use one of the following:

=========     =======================     ===================         ==========
Database      PyPi package name           Debian package name         version   
=========     =======================     ===================         ==========
mysql         MySQL-python                python-mysql                1.2.3
postgres      psycopg2                    python-psycopg2             2.4  
=========     =======================     ===================         ==========

.. note::
    The python sqlite driver is available by default with Python so no
    additional configuration is required. Also, most self-respecting systems
    have the sqlite library installed by default.


Extra depedencies
`````````````````

Synnefo provides some optional features that require specific python packages to
be installed.

**Invitations and SSH Keys generation**

=======================     ===================         ==========
PyPi package name           Debian package name         version   
=======================     ===================         ==========
pycrypto                    python-crypto               2.1.0      
=======================     ===================         ==========



Installing Synnefo package
--------------------------

Using ``pip``::

    $ pip install https://code.grnet.gr/projects/synnefo/synnefo-<version>.tar.gz --no-deps

by checking out git repository::

    $ git clone https://code.grnet.gr/git/synnefo synnefo-repo
    $ cd synnefo-repo
    $ python setup.py install

this should be enough for synnefo to get installed in your system-wide or
``virtualenv`` python installation and the following commands should be 
available from the command line::

    $ snf-manage
    $ snf-dispatcher
    $ snf-admin

Notice that Synnefo installation does not handle the creation of
``/etc/synnefo/`` directory which is the place where custom configuration 
files are loaded from. You are encouraged to create this directory and place a 
file named ``settings.conf`` with the following contents:

.. _sample-settings:
.. literalinclude:: ../_static/sample_settings.conf
    :language: python

`download <../_static/sample_settings.conf>`_

this is just to get you started on how to configure your Synnefo installation.
From this point you can continue your read to the `Initial configuration`_ section 
in this document which contains quickstart instructions for some of the initial
configuration required for Synnefo to get up and running.

For additional instructions about Synnefo settings files and what the available 
settings are, you can refer to the :ref:`configuration <configuration>` guide.


Initial configuration
---------------------

Synnefo comes with most of the required settings predefined with values that 
would cover many of the most common installation scenarios. However some basic
settings must be set be set before running Synnefo for the first time.

:ref:`sample settings file <sample-settings>`


Database
********

Change ``DATABASES`` setting based on your :ref:`database setup <database-setup>` 
and :ref:`initialize/update your database structure <database-initialization>`

.. seealso::
    :ref:`database-configuration` /
    :ref:`database-initialization`


Queue
*****

Change ``RABBIT_*`` settings to match your :ref:`RabbitMQ setup <rabbitmq-setup>`.


Backend
*******

Set ``GANETI_NODES``, ``GANETI_MASTER_IP``, ``GANETI_CLUSTER_INFO`` based on your :ref:`Ganeti
installation <ganeti-setup>` and change BACKEND_PREFIX_ID using an custom `prefix
id`.


Web application
***************

See the extended :ref:`deployment guide <webapp-deploy>` for instructions on how to
setup the Synnefo web application.

.. _database-setup:

Installing depedencies
**********************

Synnefo is written in Python 2.6 requires the some additional python packages 
to run properly.

The easiest method for installation of the Django project is to setup a
working environment through virtualenv. Alternatively, you can use your
system's package manager to install the dependencies (e.g. Macports has them
all).

You can install these packages either using `pip` python package manager::
    
    $ pip install <pypi-package-name>==<version>

or using the requirements.pip file that exists in Synnefo package repository::

    $ pip install -r requirements.pip

or Debian's `apt-get`::

    $ apt-get install <debian-package-name>


Required packages
`````````````````

.. todo::
    Confirm debian package names

=======================     ===================         ==========
PyPi package name           Debian package name         version   
=======================     ===================         ==========
django                      python-django               1.2.4      
simplejson                  python-simplejson           2.1.3
pycurl                      python-pycurl               7.19.0
python-dateutil             python-dateutil             1.4.1
IPy                         python-ipy                  0.75
south                       python-django-south         0.7.1
amqplib                     python-amqplib              0.6.1
lockfile                    python-lockfile             0.8
python-daemon               python-daemon               1.5.5
python-prctl                python-prctl                1.3.0
=======================     ===================         ==========

.. note::
    On Snow Leopard and linux (64-bit), you have to set the following
    environment variable for pip to compile the dependencies correctly::

        $ export ARCHFLAGS="-arch x86_64"

.. note::
    On Ubuntu/Debian, a few more packages must be installed before installing the
    prerequisite Python libraries::

        $ sudo aptitude install libcurl3-gnutls libcurl3-gnutls-dev uuid-dev

.. note::
    Depending on the permissions of your system’s Python, you might need to be the 
    root user to install those packages system-wide


Database driver
```````````````

Depending on the database software you choose to use one of the following:

=========     =======================     ===================         ==========
Database      PyPi package name           Debian package name         version   
=========     =======================     ===================         ==========
mysql         MySQL-python                python-mysql                1.2.3
postgres      psycopg2                    python-psycopg2             2.4  
=========     =======================     ===================         ==========

.. note::
    The python sqlite driver is available by default with Python so no
    additional configuration is required. Also, most self-respecting systems
    have the sqlite library installed by default.


Extra depedencies
`````````````````

Synnefo provides some optional features that require specific python packages to
be installed.

**Invitations and SSH Keys generation**

=======================     ===================         ==========
PyPi package name           Debian package name         version   
=======================     ===================         ==========
pycrypto                    python-crypto               2.1.0      
=======================     ===================         ==========



Installing Synnefo package
--------------------------

Using ``pip``::

    $ pip install https://code.grnet.gr/projects/synnefo/synnefo-<version>.tar.gz --no-deps

by checking out git repository::

    $ git clone https://code.grnet.gr/git/synnefo synnefo-repo
    $ cd synnefo-repo
    $ python setup.py install

this should be enough for synnefo to get installed in your system-wide or
``virtualenv`` python installation and the following commands should be 
available from the command line::

    $ snf-manage
    $ snf-dispatcher
    $ snf-admin

Notice that Synnefo installation does not handle the creation of
``/etc/synnefo/`` directory which is the place where custom configuration 
files are loaded from. You are encouraged to create this directory and place a 
file named ``settings.conf`` with the following contents:

.. _sample-settings:
.. literalinclude:: ../_static/sample_settings.conf
    :language: python

`download <../_static/sample_settings.conf>`_

this is just to get you started on how to configure your Synnefo installation.
From this point you can continue your read to the `Initial configuration`_ section 
in this document which contains quickstart instructions for some of the initial
configuration required for Synnefo to get up and running.

For additional instructions about Synnefo settings files and what the available 
settings are, you can refer to the :ref:`configuration <configuration>` guide.


Initial configuration
---------------------

Synnefo comes with most of the required settings predefined with values that 
would cover many of the most common installation scenarios. However some basic
settings must be set be set before running Synnefo for the first time.

:ref:`sample settings file <sample-settings>`


Database
********

Change ``DATABASES`` setting based on your :ref:`database setup <database-setup>` 
and :ref:`initialize/update your database structure <database-initialization>`

.. seealso::
    :ref:`database-configuration` /
    :ref:`database-initialization`


Queue
*****

Change ``RABBIT_*`` settings to match your :ref:`RabbitMQ setup <rabbitmq-setup>`.


Backend
*******

Set ``GANETI_NODES``, ``GANETI_MASTER_IP``, ``GANETI_CLUSTER_INFO`` based on your :ref:`Ganeti
installation <ganeti-setup>` and change BACKEND_PREFIX_ID using an custom `prefix
id`.


Web application
***************

See the extended :ref:`deployment guide <webapp-deploy>` for instructions on how to
setup the Synnefo web application.
