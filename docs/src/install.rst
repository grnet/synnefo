Installation
============

This document describes the basic steps to obtain a basic, working Synnefo
deployment. 

The Synnefo package needs to be installed on nodes of type :ref:`APISERVER_NODE`, 
:ref:`LOGIC_NODE` and :ref:`WEBAPP_NODE` nodes with properly configured  
:ref:`settings <configuration>`. 

This guide also covers in some detail instructions on how to set up additional
additional software required by Synnefo to run properly.


Prerequisites
-------------


.. _ganeti-setup:

Ganeti installation
*******************
Synnefo requires a working Ganeti installation at the backend. Installation
of Ganeti is not covered by this document, please refer to
`ganeti documentation <http://docs.ganeti.org/ganeti/current/html>`_ for all the 
gory details. A successful Ganeti installation concludes with a working 
:ref:`GANETI-MASTER <GANETI_NODES>` and a number of :ref:`GANETI-NODEs <GANETI_NODES>`.


Ganeti monitoring daemon
````````````````````````
The Ganeti monitoring daemon must run on GANETI-MASTER.
The monitoring daemon is configured through ``/etc/synnefo/ganeti.conf``.
An example is provided under ``snf-ganeti-tools/``.

If run from the repository directory, make sure to have snf-ganeti-tools/
in the ``PYTHONPATH``.
You may also build Debian packages directly from the repository::

    $ cd snf-ganeti-tools
    $ dpkg-buildpackage -b -uc -us
    $ dpkg -i ../snf-ganeti-tools-*deb

.. todo::
    how to handle master migration.


Synnefo Ganeti hook
```````````````````
The generic Synnefo Ganeti hook wrapper resides in the snf-ganeti-tools/
directory of the Synnefo repository.

The hook needs to be enabled for phases `post-{add,modify,reboot,start,stop}`
by *symlinking* in ``/etc/ganeti/hooks/instance-{add,modify,reboot,start,stop}-post.d`` 
on GANETI-MASTER, e.g. ::

    root@ganeti-master:/etc/ganeti/hooks/instance-start-post.d# ls -l
    lrwxrwxrwx 1 root root 45 May   3 13:45 00-snf-ganeti-hook -> /home/devel/synnefo/snf-ganeti-hook/snf-ganeti-hook.py

.. note::
    The link name may only contain "upper and lower case, digits,
    underscores and hyphens. In other words, the regexp ^[a-zA-Z0-9_-]+$."

.. seealso::
    `Ganeti customisation using hooks <http://docs.ganeti.org/ganeti/master/html/hooks.html?highlight=hooks#naming>`_

If run from the repository directory, make sure to have `snf-ganeti-tools/`
in the ``PYTHONPATH``.

Alternative, build Debian packages which take care of building, installing
and activating the Ganeti hook automatically, see step. 9.


vncauthproxy
************
To support OOB console access to the VMs over VNC, the vncauthproxy
daemon must be running on every node of type APISERVER.

Download and install vncauthproxy from its own repository,
at `https://code.grnet.gr/git/vncauthproxy` (known good commit: tag v1.0).

Download and install a specific repository commit::

    $ bin/pip install -e git+https://code.grnet.gr/git/vncauthproxy@INSERT_COMMIT_HERE#egg=vncauthproxy

Create ``/var/log/vncauthproxy`` and set its permissions appropriately.

Alternatively, you can build Debian packages. To do so,
checkout the "debian" branch of the vncauthproxy repository
(known good commit: tag debian/v1.0)::

    $ git checkout debian

Then build debian package, and install as root::

    $ dpkg-buildpackage -b -uc -us
    $ dpkg -i ../vncauthproxy_1.0-1_all.deb

.. warning::
    **Failure to build the package on the Mac.**

    ``libevent``, a requirement for gevent which in turn is a requirement for
    vncauthproxy is not included in `MacOSX` by default and installing it with
    MacPorts does not lead to a version that can be found by the gevent
    build process. A quick workaround is to execute the following commands::

        cd $SYNNEFO
        sudo pip install -e git+https://code.grnet.gr/git/vncauthproxy@5a196d8481e171a#egg=vncauthproxy
        <the above fails>
        cd build/gevent
        sudo python setup.py -I/opt/local/include -L/opt/local/lib build
        cd $SYNNEFO
        sudo pip install -e git+https://code.grnet.gr/git/vncauthproxy@5a196d8481e171a#egg=vncauthproxy

NFDHCPD installation
********************
Setup Synnefo-specific networking on the Ganeti backend.
This part is deployment-specific and must be customized based on the
specific needs of the system administrators.

A reference installation will use a Synnefo-specific KVM ifup script,
NFDHCPD and pre-provisioned Linux bridges to support public and private
network functionality. For this:

Grab NFDHCPD from its own repository (https://code.grnet.gr/git/nfdhcpd),
install it, modify /etc/nfdhcpd/nfdhcpd.conf to reflect your network
configuration.

Install a custom KVM ifup script for use by Ganeti, as
``/etc/ganeti/kvm-vif-bridge``, on GANETI-NODEs. A sample implementation is
provided under ``/contrib/ganeti-hooks``. Set ``NFDHCPD_STATE_DIR`` to point
to NFDHCPD's state directory, usually ``/var/lib/nfdhcpd``.


.. _rabbitmq-setup:

RabbitMQ installation
*********************
RabbitMQ is used as a generic message broker for the system. It should be
installed on two seperate QUEUE nodes (VMs should be enough for the moment)
in a high availability configuration as described here:

    http://www.rabbitmq.com/pacemaker.html

After installation, create a user and set its permissions::

    $ rabbitmqctl add_user <username> <password>
    $ rabbitmqctl set_permissions -p / <username>  "^.*" ".*" ".*"

The values set for the user and password must be mirrored in the
`RABBIT_*` variables in your `settings`_ (see step 6)


snf-image installation
**********************
Installation of the `snf-image` `Ganeti OS provider` for image deployment.

For Synnefo to be able to launch VMs from specified Images, you need
the snf-image OS Provider installed on *all* Ganeti nodes.

Please see `https://code.grnet.gr/projects/snf-image/wiki`
for installation instructions and documentation on the design
and implementation of snf-image.

Please see `https://code.grnet.gr/projects/snf-image/files`
for the latest packages.

Images should be stored under extdump format in a directory
of your choice, configurable as ``IMAGE_DIR`` in ``/etc/default/snf-image``.


.. _database-setup:

Database installation
*********************

SQLite
``````
Most self-respecting systems have the sqlite library installed by default.

MySQL
`````
MySQL must be installed first::

    $ sudo apt-get install libmysqlclient-dev

if you are using MacPorts::

    $ sudo port install mysql5

.. note::
    On MacOSX with Mysql install from MacPorts the above command will
    fail complaining that it cannot find the mysql_config command. Do
    the following and restart the installation::

	    $ echo "mysql_config = /opt/local/bin/mysql_config5" >> ./build/MySQL-python/site.cfg

Configure a MySQL db/account for synnefo::

    $ mysql -u root -p;

    mysql> create database <database name>;
    mysql> show databases;
    mysql> GRANT ALL on <database name>.* TO <db username> IDENTIFIED BY '<db password>';

.. warning::
        MySQL *must* be set in READ-COMMITED mode, e.g. by setting::

            transaction-isolation = READ-COMMITTED
            
        in the [mysqld] section of /etc/mysql/my.cnf.

        Alternatively, make sure the following code fragment stays enabled
        in /etc/synnefo/10-database.conf file:
        
        .. code-block:: python

            if DATABASES['default']['ENGINE'].endswith('mysql'):
                DATABASES['default']['OPTIONS'] = {
                        'init_command': 'SET storage_engine=INNODB; ' +
                            'SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED',
                }
          
PostgreSQL
``````````
You need to install the PostgreSQL binaries::
	     
    $ sudo apt-get install postgresql-8.4 libpq-dev

or ir you are using MacPorts::

    $ sudo port install postgresql84

To configure a postgres db/account for synnefo,

* Become the postgres user, connect to PostgreSQL::

       $ sudo su - postgres
       $ psql
	
* Run the following commands::

	   DROP DATABASE <database name>;
	   DROP USER <db username>;
	   CREATE USER <db username> WITH PASSWORD '<db password>';
	   CREATE DATABASE <database name>;
	   GRANT ALL PRIVILEGES ON DATABASE <database name> TO <db username>;
	   ALTER DATABASE <database name> OWNER TO <db username>;
	   ALTER USER <db username> CREATEDB;
       
.. note:: 
   The last line enables the newly created user to create own databases. This
   is needed for Django to create and drop the test_synnefo database for unit
   testing.



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
pycurl                      python-curl                 7.19.0
python-dateutil             python-dateutil             1.4.1
IPy                         python-ipy                  0.75
south                       python-south                0.7.1
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

    $ pip install https://code.grnet.gr/projects/synnefo/synnefo-<version>.tar.gz

by checking out git repository::

    $ git clone https://code.grnet.gr/git/synnefo synnefo-repo
    $ cd synnefo-repo
    $ python setup.py install

this should be enough for synnefo to get installed in your system-wide or
``virtualenv`` python installation and the following commands should be 
available from the command line::

    $ synnefo-manage
    $ synnefo-dispatcher
    $ synnefo-admin

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

Changes ``DATABASES`` setting based on your :ref:`database setup <database-setup>` 
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
