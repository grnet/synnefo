Installation
============

This document describes the basic steps to obtain a basic, working Synnefo
deployment. 

As of v0.5 the Synnefo Django project needs to be installed on nodes of 
type `APISERVER`_, `LOGIC`_ and `WEBAPP`_ nodes with properly configured 
:ref:`settings`. 



Prerequisites
-------------

Ganeti installation
*******************
Synnefo requires a working Ganeti installation at the backend. Installation
of Ganeti is not covered by this document, please refer to
`ganeti documentation <http://docs.ganeti.org/ganeti/current/html>`_ for all the 
gory details. A successful Ganeti installation concludes with a working 
`GANETI-MASTER`_ and a number of `GANETI-NODEs`_.


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
----------------------

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
*****************

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
***************

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
*****************

Synnefo provides some optional features that require specific python packages to
be install.

**Invitations and SSH Keys generation**

=======================     ===================         ==========
PyPi package name           Debian package name         version   
=======================     ===================         ==========
pycrypto                    python-crypto               2.1.0      
=======================     ===================         ==========



Installation of the Synnefo package
-----------------------------------


Configuring Synnefo
-------------------

The settings.py file for Django may be derived by concatenating the
settings.py.dist file contained in the Synnefo distribution with a file
containing custom modifications, which shall override all settings deviating
from the supplied settings.py.dist. This is recommended to minimize the load
of reconstructing settings.py from scratch, since each release currently
brings heavy changes to settings.py.dist.

Add the following to your custom settings.py, depending on your choice
of DB:

SQLite
``````
.. code-block:: python

    PROJECT_PATH = os.path.dirname(os.path.abspath(__file__)) + '/'

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': PROJECT_PATH + 'synnefo.db'
        }
    }

.. warning:: `NAME` must be an absolute path to the sqlite3 database file

MySQL
`````
.. code-block:: python

    DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.mysql',
             'NAME': 'synnefo',
             'USER': 'USERNAME',
             'PASSWORD': 'PASSWORD',
             'HOST': 'HOST',
             'PORT': 'PORT',
             'OPTIONS': {
                 'init_command': 'SET storage_engine=INNODB',
             }
        }
    }

PostgreSQL
``````````

.. code-block:: python

    DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.postgresql_psycopg2',
             'NAME': 'DATABASE',
             'USER': 'USERNAME',
             'PASSWORD': 'PASSWORD',
             'HOST': 'HOST',
             'PORT': 'PORT',
         }
    }

Try it out. The following command will attempt to connect to the DB and
print out DDL statements. It should not fail.

$ ./bin/python manage.py sql db


7. Initialization of Synnefo DB:
   You need to initialize the Synnefo DB and load fixtures
   db/fixtures/{users,flavors,images}.json, which make the API usable by end
   users by defining a sample set of users, hardware configurations (flavors)
   and OS images.

   IMPORTANT: Be sure to modify db/fixtures/users.json and select
   a unique token for each of the initial and any other users defined in this
   file. DO NOT LEAVE THE SAMPLE AUTHENTICATION TOKENS enabled in deployed
   configurations.

     $ ./bin/python manage.py syncdb
     $ ./bin/python manage.py migrate
     $ ./bin/python manage.py loaddata db/fixtures/users.json
     $ ./bin/python manage.py loaddata db/fixtures/flavors.json
     $ ./bin/python manage.py loaddata db/fixtures/images.json


8. Finalization of settings.py:
   Set the BACKEND_PREFIX_ID variable to some unique prefix, e.g. your commit
   username in settings.py. Several functional conventions within the system
   require this variable to include a dash at its end (e.g. snf-)


9. Installation of the Ganeti monitoring daemon, /ganeti/snf-ganeti-eventd:
   The Ganeti monitoring daemon must run on GANETI-MASTER.

   The monitoring daemon is configured through /etc/synnefo/settings.conf.
   An example is provided under snf-ganeti-tools/.

   If run from the repository directory, make sure to have snf-ganeti-tools/
   in the PYTHONPATH.

   You may also build Debian packages directly from the repository:
   $ cd snf-ganeti-tools
   $ dpkg-buildpackage -b -uc -us
   # dpkg -i ../snf-ganeti-tools-*deb

   TBD: how to handle master migration.


10. Installation of the Synnefo dispatcher, /logic/dispatcher.py:
    The logic dispatcher is part of the Synnefo Django project and must run
    on LOGIC nodes.

    The dispatcher retrieves messages from the queue and calls the appropriate
    handler function as defined in the queue configuration in `setttings.py'.
    The default configuration should work directly without any modifications.

    For the time being The dispatcher must be run by hand:
      $ ./bin/python ./logic/dispatcher.py

    The dispatcher should run in at least 2 instances to ensure high
    (actually, increased) availability.


11. Installation of the Synnefo Ganeti hook:
    The generic Synnefo Ganeti hook wrapper resides in the snf-ganeti-tools/
    directory of the Synnefo repository.

    The hook needs to be enabled for phases post-{add,modify,reboot,start,stop}
    by *symlinking* in
    /etc/ganeti/hooks/instance-{add,modify,reboot,start,stop}-post.d on
    GANETI-MASTER, e.g.:

    root@ganeti-master:/etc/ganeti/hooks/instance-start-post.d# ls -l
    lrwxrwxrwx 1 root root 45 May   3 13:45 00-snf-ganeti-hook -> /home/devel/synnefo/snf-ganeti-hook/snf-ganeti-hook.py

    IMPORTANT: The link name may only contain "upper and lower case, digits,
    underscores and hyphens. In other words, the regexp ^[a-zA-Z0-9_-]+$."
    See:
    http://docs.ganeti.org/ganeti/master/html/hooks.html?highlight=hooks#naming

    If run from the repository directory, make sure to have snf-ganeti-tools/
    in the PYTHONPATH.

    Alternative, build Debian packages which take care of building, installing
    and activating the Ganeti hook automatically, see step. 9.


12. Installation of the VNC authentication proxy, vncauthproxy:
    To support OOB console access to the VMs over VNC, the vncauthproxy
    daemon must be running on every node of type APISERVER.

    Download and install vncauthproxy from its own repository,
    at https://code.grnet.gr/git/vncauthproxy (known good commit: tag v1.0).

    Download and install a specific repository commit:

    $ bin/pip install -e git+https://code.grnet.gr/git/vncauthproxy@INSERT_COMMIT_HERE#egg=vncauthproxy

    Create /var/log/vncauthproxy and set its permissions appropriately.

    Alternatively, you can build Debian packages. To do so,
    checkout the "debian" branch of the vncauthproxy repository
    (known good commit: tag debian/v1.0):

    $ git checkout debian

    Then build debian package, and install as root:

    $ dpkg-buildpackage -b -uc -us
    # dpkg -i ../vncauthproxy_1.0-1_all.deb

    --Failure to build the package on the Mac.

    libevent, a requirement for gevent which in turn is a requirement for
    vncauthproxy is not included in MacOSX by default and installing it with
    MacPorts does not lead to a version that can be found by the gevent
    build process. A quick workaround is to execute the following commands:

    cd $SYNNEFO
    sudo pip install -e git+https://code.grnet.gr/git/vncauthproxy@5a196d8481e171a#egg=vncauthproxy
    <the above fails>
    cd build/gevent
    sudo python setup.py -I/opt/local/include -L/opt/local/lib build
    cd $SYNNEFO
    sudo pip install -e git+https://code.grnet.gr/git/vncauthproxy@5a196d8481e171a#egg=vncauthproxy


13. Installation of the snf-image Ganeti OS provider for image deployment:
    For Synnefo to be able to launch VMs from specified Images, you need
    the snf-image OS Provider installed on *all* Ganeti nodes.

    Please see https://code.grnet.gr/projects/snf-image/wiki
    for installation instructions and documentation on the design
    and implementation of snf-image.

    Please see https://code.grnet.gr/projects/snf-image/files
    for the latest packages.

    Images should be stored under extdump format in a directory
    of your choice, configurable as IMAGE_DIR in /etc/default/snf-image.


14. Setup Synnefo-specific networking on the Ganeti backend:
    This part is deployment-specific and must be customized based on the
    specific needs of the system administrators.

    A reference installation will use a Synnefo-specific KVM ifup script,
    NFDHCPD and pre-provisioned Linux bridges to support public and private
    network functionality. For this:

    Grab NFDHCPD from its own repository (https://code.grnet.gr/git/nfdhcpd),
    install it, modify /etc/nfdhcpd/nfdhcpd.conf to reflect your network
    configuration.

    Install a custom KVM ifup script for use by Ganeti, as
    /etc/ganeti/kvm-vif-bridge, on GANETI-NODEs. A sample implementation is
    provided under /contrib/ganeti-hooks. Set NFDHCPD_STATE_DIR to point
    to NFDHCPD's state directory, usually /var/lib/nfdhcpd.


15. See section "Logging" in README.admin, and edit settings.d/00-logging.conf
    according to your OS and individual deployment characteristics.


16. Optionally, read the okeanos_site/README file to setup ~okeanos introductory 
    site (intro, video/info pages). Please see okeanos_site/90-okeanos.sample
    for a sample configuration file which overrides site-specific variables,
    to be placed under settings.d/, after customization.


17. (Hopefully) Done


