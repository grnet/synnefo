.. _quick-install-admin-guide:

Administrator's Quick Installation Guide
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is the Administrator's quick installation guide.

It describes how to install the whole synnefo stack on two (2) physical nodes,
with minimum configuration. It installs synnefo from Debian packages, and
assumes the nodes run Debian Squeeze. After successful installation, you will
have the following services running:

 * Identity Management (Astakos)
 * Object Storage Service (Pithos+)
 * Compute Service (Cyclades)
 * Image Registry Service (Plankton)

and a single unified Web UI to manage them all.

The Volume Storage Service (Archipelago) and the Billing Service (Aquarium) are
not released yet.

If you just want to install the Object Storage Service (Pithos+), follow the guide
and just stop after the "Testing of Pithos+" section.


Installation of Synnefo / Introduction
======================================

We will install the services with the above list's order. Cyclades and Plankton
will be installed in a single step (at the end), because at the moment they are
contained in the same software component. Furthermore, we will install all
services in the first physical node, except Pithos+ which will be installed in
the second, due to a conflict between the snf-pithos-app and snf-cyclades-app
component (scheduled to be fixed in the next version).

For the rest of the documentation we will refer to the first physical node as
"node1" and the second as "node2". We will also assume that their domain names
are "node1.example.com" and "node2.example.com" and their IPs are "4.3.2.1" and
"4.3.2.2" respectively.


General Prerequisites
=====================

These are the general synnefo prerequisites, that you need on node1 and node2
and are related to all the services (Astakos, Pithos+, Cyclades, Plankton).

To be able to download all synnefo components you need to add the following
lines in your ``/etc/apt/sources.list`` file:

| ``deb http://apt.dev.grnet.gr squeeze main``
| ``deb-src http://apt.dev.grnet.gr squeeze main``

You also need a shared directory visible by both nodes. Pithos+ will save all
data inside this directory. By 'all data', we mean files, images, and pithos
specific mapping data. If you plan to upload more than one basic image, this
directory should have at least 50GB of free space. During this guide, we will
assume that node1 acts as an NFS server and serves the directory ``/srv/pithos``
to node2. Node2 has this directory mounted under ``/srv/pithos``, too.

Before starting the synnefo installation, you will need basic third party
software to be installed and configured on the physical nodes. We will describe
each node's general prerequisites separately. Any additional configuration,
specific to a synnefo service for each node, will be described at the service's
section.

Node1
-----

General Synnefo dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

 * apache (http server)
 * gunicorn (WSGI http server)
 * postgresql (database)
 * rabbitmq (message queue)

You can install the above by running:

.. code-block:: console

   # apt-get install apache2 postgresql rabbitmq-server

Make sure to install gunicorn >= v0.12.2. You can do this by installing from
the official debian backports:

.. code-block:: console

   # apt-get -t squeeze-backports install gunicorn

On node1, we will create our databases, so you will also need the
python-psycopg2 package:

.. code-block:: console

   # apt-get install python-psycopg2

Database setup
~~~~~~~~~~~~~~

On node1, we create a database called ``snf_apps``, that will host all django
apps related tables. We also create the user ``synnefo`` and grant him all
privileges on the database. We do this by running:

.. code-block:: console

   root@node1:~ # su - postgres
   postgres@node1:~ $ psql
   postgres=# CREATE DATABASE snf_apps WITH ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C' TEMPLATE=template0;
   postgres=# CREATE USER synnefo WITH PASSWORD 'example_passw0rd';
   postgres=# GRANT ALL PRIVILEGES ON DATABASE snf_apps TO synnefo;

We also create the database ``snf_pithos`` needed by the pithos+ backend and
grant the ``synnefo`` user all privileges on the database. This database could
be created on node2 instead, but we do it on node1 for simplicity. We will
create all needed databases on node1 and then node2 will connect to them.

.. code-block:: console

   postgres=# CREATE DATABASE snf_pithos WITH ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C' TEMPLATE=template0;
   postgres=# GRANT ALL PRIVILEGES ON DATABASE snf_pithos TO synnefo;

Configure the database to listen to all network interfaces. You can do this by
editting the file ``/etc/postgresql/8.4/main/postgresql.conf`` and change
``listen_addresses`` to ``'*'`` :

.. code-block:: console

   listen_addresses = '*'

Furthermore, edit ``/etc/postgresql/8.4/main/pg_hba.conf`` to allow node1 and
node2 to connect to the database. Add the following lines under ``#IPv4 local
connections:`` :

.. code-block:: console

   host		all	all	4.3.2.1/32	md5
   host		all	all	4.3.2.2/32	md5

Make sure to substitute "4.3.2.1" and "4.3.2.2" with node1's and node2's
actual IPs. Now, restart the server to apply the changes:

.. code-block:: console

   # /etc/init.d/postgresql restart

Gunicorn setup
~~~~~~~~~~~~~~

Create the file ``synnefo`` under ``/etc/gunicorn.d/`` containing the following:

.. code-block:: console

   CONFIG = {
    'mode': 'django',
    'environment': {
      'DJANGO_SETTINGS_MODULE': 'synnefo.settings',
    },
    'working_dir': '/etc/synnefo',
    'user': 'www-data',
    'group': 'www-data',
    'args': (
      '--bind=127.0.0.1:8080',
      '--workers=4',
      '--log-level=debug',
    ),
   }

.. warning:: Do NOT start the server yet, because it won't find the
    ``synnefo.settings`` module. We will start the server after successful
    installation of astakos. If the server is running::

       # /etc/init.d/gunicorn stop

Apache2 setup
~~~~~~~~~~~~~

Create the file ``synnefo`` under ``/etc/apache2/sites-available/`` containing
the following:

.. code-block:: console

   <VirtualHost *:80>
     ServerName node1.example.com

     RewriteEngine On
     RewriteCond %{THE_REQUEST} ^.*(\\r|\\n|%0A|%0D).* [NC]
     RewriteRule ^(.*)$ - [F,L]
     RewriteRule (.*) https://%{HTTP_HOST}%{REQUEST_URI}
   </VirtualHost>

Create the file ``synnefo-ssl`` under ``/etc/apache2/sites-available/``
containing the following:

.. code-block:: console

   <IfModule mod_ssl.c>
   <VirtualHost _default_:443>
     ServerName node1.example.com

     Alias /static "/usr/share/synnefo/static"

   #  SetEnv no-gzip
   #  SetEnv dont-vary

     AllowEncodedSlashes On

     RequestHeader set X-Forwarded-Protocol "https"

     <Proxy * >
       Order allow,deny
       Allow from all
     </Proxy>

     SetEnv                proxy-sendchunked
     SSLProxyEngine        off
     ProxyErrorOverride    off

     ProxyPass        /static !
     ProxyPass        / http://localhost:8080/ retry=0
     ProxyPassReverse / http://localhost:8080/

     RewriteEngine On
     RewriteCond %{THE_REQUEST} ^.*(\\r|\\n|%0A|%0D).* [NC]
     RewriteRule ^(.*)$ - [F,L]
     RewriteRule ^/login(.*) /im/login/redirect$1 [PT,NE]

     SSLEngine on
     SSLCertificateFile    /etc/ssl/certs/ssl-cert-snakeoil.pem
     SSLCertificateKeyFile /etc/ssl/private/ssl-cert-snakeoil.key
   </VirtualHost>
   </IfModule>

Now enable sites and modules by running:

.. code-block:: console

   # a2enmod ssl
   # a2enmod rewrite
   # a2dissite default
   # a2ensite synnefo
   # a2ensite synnefo-ssl
   # a2enmod headers
   # a2enmod proxy_http

.. warning:: Do NOT start/restart the server yet. If the server is running::

       # /etc/init.d/apache2 stop

Message Queue setup
~~~~~~~~~~~~~~~~~~~

The message queue will run on node1, so we need to create the appropriate
rabbitmq user. The user is named ``synnefo`` and gets full privileges on all
exchanges:

.. code-block:: console

   # rabbitmqctl add_user synnefo "examle_rabbitmq_passw0rd"
   # rabbitmqctl set_permissions synnefo ".*" ".*" ".*"

We do not need to initialize the exchanges. This will be done automatically,
during the Cyclades setup.

Pithos+ data directory setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As mentioned in the General Prerequisites section, there is a directory called
``/srv/pithos`` visible by both nodes. We create and setup the ``data``
directory inside it:

.. code-block:: console

   # cd /srv/pithos
   # mkdir data
   # chown www-data:www-data data
   # chmod g+ws data

You are now ready with all general prerequisites concerning node1. Let's go to
node2.

Node2
-----

General Synnefo dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

 * apache (http server)
 * gunicorn (WSGI http server)
 * postgresql (database)

You can install the above by running:

.. code-block:: console

   # apt-get install apache2 postgresql

Make sure to install gunicorn >= v0.12.2. You can do this by installing from
the official debian backports:

.. code-block:: console

   # apt-get -t squeeze-backports install gunicorn

Node2 will connect to the databases on node1, so you will also need the
python-psycopg2 package:

.. code-block:: console

   # apt-get install python-psycopg2

Database setup
~~~~~~~~~~~~~~

All databases have been created and setup on node1, so we do not need to take
any action here. From node2, we will just connect to them. When you get familiar
with the software you may choose to run different databases on different nodes,
for performance/scalability/redundancy reasons, but those kind of setups are out
of the purpose of this guide.

Gunicorn setup
~~~~~~~~~~~~~~

Create the file ``synnefo`` under ``/etc/gunicorn.d/`` containing the following
(same contents as in node1; you can just copy/paste the file):

.. code-block:: console

   CONFIG = {
    'mode': 'django',
    'environment': {
      'DJANGO_SETTINGS_MODULE': 'synnefo.settings',
    },
    'working_dir': '/etc/synnefo',
    'user': 'www-data',
    'group': 'www-data',
    'args': (
      '--bind=127.0.0.1:8080',
      '--workers=4',
      '--log-level=debug',
      '--timeout=43200'
    ),
   }

.. warning:: Do NOT start the server yet, because it won't find the
    ``synnefo.settings`` module. We will start the server after successful
    installation of astakos. If the server is running::

       # /etc/init.d/gunicorn stop

Apache2 setup
~~~~~~~~~~~~~

Create the file ``synnefo`` under ``/etc/apache2/sites-available/`` containing
the following:

.. code-block:: console

   <VirtualHost *:80>
     ServerName node2.example.com

     RewriteEngine On
     RewriteCond %{THE_REQUEST} ^.*(\\r|\\n|%0A|%0D).* [NC]
     RewriteRule ^(.*)$ - [F,L]
     RewriteRule (.*) https://%{HTTP_HOST}%{REQUEST_URI}
   </VirtualHost>

Create the file ``synnefo-ssl`` under ``/etc/apache2/sites-available/``
containing the following:

.. code-block:: console

   <IfModule mod_ssl.c>
   <VirtualHost _default_:443>
     ServerName node2.example.com

     Alias /static "/usr/share/synnefo/static"

     SetEnv no-gzip
     SetEnv dont-vary
     AllowEncodedSlashes On

     RequestHeader set X-Forwarded-Protocol "https"

     <Proxy * >
       Order allow,deny
       Allow from all
     </Proxy>

     SetEnv                proxy-sendchunked
     SSLProxyEngine        off
     ProxyErrorOverride    off

     ProxyPass        /static !
     ProxyPass        / http://localhost:8080/ retry=0
     ProxyPassReverse / http://localhost:8080/

     SSLEngine on
     SSLCertificateFile    /etc/ssl/certs/ssl-cert-snakeoil.pem
     SSLCertificateKeyFile /etc/ssl/private/ssl-cert-snakeoil.key
   </VirtualHost>
   </IfModule>

As in node1, enable sites and modules by running:

.. code-block:: console

   # a2enmod ssl
   # a2enmod rewrite
   # a2dissite default
   # a2ensite synnefo
   # a2ensite synnefo-ssl
   # a2enmod headers
   # a2enmod proxy_http

.. warning:: Do NOT start/restart the server yet. If the server is running::

       # /etc/init.d/apache2 stop

We are now ready with all general prerequisites for node2. Now that we have
finished with all general prerequisites for both nodes, we can start installing
the services. First, let's install Astakos on node1.


Installation of Astakos on node1
================================

To install astakos, grab the package from our repository (make sure  you made
the additions needed in your ``/etc/apt/sources.list`` file, as described
previously), by running:

.. code-block:: console

   # apt-get install snf-astakos-app

After successful installation of snf-astakos-app, make sure that also
snf-webproject has been installed (marked as "Recommended" package). By default
Debian installs "Recommended" packages, but if you have changed your
configuration and the package didn't install automatically, you should
explicitly install it manually running:

.. code-block:: console

   # apt-get install snf-webproject

The reason snf-webproject is "Recommended" and not a hard dependency, is to give
the experienced administrator the ability to install synnefo in a custom made
django project. This corner case concerns only very advanced users that know
what they are doing and want to experiment with synnefo.

Configuration of Astakos
========================

Conf Files
----------

After astakos is successfully installed, you will find the directory
``/etc/synnefo`` and some configuration files inside it. The files contain
commented configuration options, which are the default options. While installing
new snf-* components, new configuration files will appear inside the directory.
In this guide (and for all services), we will edit only the minimum necessary
configuration options, to reflect our setup. Everything else will remain as is.

After getting familiar with synnefo, you will be able to customize the software
as you wish and fits your needs. Many options are available, to empower the
administrator with extensively customizable setups.

For the snf-webproject component (installed as an astakos dependency), we
need the following:

Edit ``/etc/synnefo/10-snf-webproject-database.conf``. You will need to
uncomment and edit the ``DATABASES`` block to reflect our database:

.. code-block:: console

   DATABASES = {
    'default': {
        # 'postgresql_psycopg2', 'postgresql','mysql', 'sqlite3' or 'oracle'
        'ENGINE': 'postgresql_psycopg2',
         # ATTENTION: This *must* be the absolute path if using sqlite3.
         # See: http://docs.djangoproject.com/en/dev/ref/settings/#name
        'NAME': 'snf_apps',
        'USER': 'synnefo',                      # Not used with sqlite3.
        'PASSWORD': 'examle_passw0rd',          # Not used with sqlite3.
        # Set to empty string for localhost. Not used with sqlite3.
        'HOST': '4.3.2.1',
        # Set to empty string for default. Not used with sqlite3.
        'PORT': '5432',
    }
   }

Edit ``/etc/synnefo/10-snf-webproject-deploy.conf``. Uncomment and edit
``SECRET_KEY``. This is a django specific setting which is used to provide a
seed in secret-key hashing algorithms. Set this to a random string of your
choise and keep it private:

.. code-block:: console

   SECRET_KEY = 'sy6)mw6a7x%n)-example_secret_key#zzk4jo6f2=uqu!1o%)'

For astakos specific configuration, edit the following options in
``/etc/synnefo/20-snf-astakos-app-settings.conf`` :

.. code-block:: console

   ASTAKOS_IM_MODULES = ['local']

   ASTAKOS_COOKIE_DOMAIN = '.example.com'

   ASTAKOS_BASEURL = 'https://node1.example.com'

   ASTAKOS_SITENAME = '~okeanos demo example'

   ASTAKOS_CLOUD_SERVICES = (
           { 'url':'https://node1.example.com/im/', 'name':'~okeanos home', 'id':'cloud', 'icon':'home-icon.png' },
           { 'url':'https://node1.example.com/ui/', 'name':'cyclades', 'id':'cyclades' },
           { 'url':'https://node2.example.com/ui/', 'name':'pithos+', 'id':'pithos' })

   ASTAKOS_RECAPTCHA_PUBLIC_KEY = 'example_recaptcha_public_key!@#$%^&*('
   ASTAKOS_RECAPTCHA_PRIVATE_KEY = 'example_recaptcha_private_key!@#$%^&*('

   ASTAKOS_RECAPTCHA_USE_SSL = True

``ASTAKOS_IM_MODULES`` refers to the astakos login methods. For now only local
is supported. The ``ASTAKOS_COOKIE_DOMAIN`` should be the base url of our
domain (for all services). ``ASTAKOS_BASEURL`` is the astakos home page.
``ASTAKOS_CLOUD_SERVICES`` contains all services visible to and served by
astakos. The first element of the dictionary is used to point to a generic
landing page for your services (cyclades, pithos). If you don't have such a
page it can be omitted. The second and third element point to our services
themselves (the apps) and should be set as above.

For the ``ASTAKOS_RECAPTCHA_PUBLIC_KEY`` and ``ASTAKOS_RECAPTCHA_PRIVATE_KEY``
go to https://www.google.com/recaptcha/admin/create and create your own pair.

Shibboleth Setup
----------------
Optionally, Astakos can delegate user authentication to a Shibboleth federation.

To setup shibboleth, install package::

  apt-get install libapache2-mod-shib2

Change appropriately the configuration files in ``/etc/shibboleth``.

Add in ``/etc/apache2/sites-available/synnefo-ssl``::

  ShibConfig /etc/shibboleth/shibboleth2.xml
  Alias      /shibboleth-sp /usr/share/shibboleth

  <Location /im/login/shibboleth>
    AuthType shibboleth
    ShibRequireSession On
    ShibUseHeaders On
    require valid-user
  </Location>

and before the line containing::

  ProxyPass        / http://localhost:8080/ retry=0

add::

  ProxyPass /Shibboleth.sso !

Then, enable the shibboleth module::

  a2enmod shib2

After passing through the apache module, the following tokens should be available at the destination::

  eppn # eduPersonPrincipalName
  Shib-InetOrgPerson-givenName
  Shib-Person-surname
  Shib-Person-commonName
  Shib-InetOrgPerson-displayName
  Shib-EP-Affiliation
  Shib-Session-ID

Finally, add 'shibboleth' in ``ASTAKOS_IM_MODULES``.

Servers Initialization
----------------------

After configuration is done, we initialize the servers on node1:

.. code-block:: console

   root@node1:~ # /etc/init.d/gunicorn restart
   root@node1:~ # /etc/init.d/apache2 restart

Database Initialization
-----------------------

Then, we initialize the database by running:

.. code-block:: console

   # snf-manage syncdb

At this example we don't need to create a django superuser, so we select
``[no]`` to the question. After a successful sync, we run the migration needed
for astakos:

.. code-block:: console

   # snf-manage migrate im

Finally we load the pre-defined user groups

.. code-block:: console

   # snf-manage loaddata groups

You have now finished the Astakos setup. Let's test it now.


Testing of Astakos
==================

Open your favorite browser and go to:

``http://node1.example.com/im``

If this redirects you to ``https://node1.example.com/im`` and you can see
the "welcome" door of Astakos, then you have successfully setup Astakos.

Let's create our first user. At the homepage click the "CREATE ACCOUNT" button
and fill all your data at the sign up form. Then click "SUBMIT". You should now
see a green box on the top, which informs you that you made a successful request
and the request has been sent to the administrators. So far so good.

Now we need to activate that user. Return to a command prompt at node1 and run:

.. code-block:: console

   root@node1:~ # snf-manage listusers

This command should show you a list with only one user; the one we just created.
This user should have an id with a value of ``1``. It should also have an
"active" status with the value of ``0`` (inactive). Now run:

.. code-block:: console

   root@node1:~ # snf-manage modifyuser --set-active 1

This modifies the active value to ``1``, and actually activates the user.
When running in production, the activation is done automatically with different
types of moderation, that Astakos supports. You can see the moderation methods
(by invitation, whitelists, matching regexp, etc.) at the Astakos specific
documentation. In production, you can also manually activate a user, by sending
him/her an activation email. See how to do this at the :ref:`User
activation <user_activation>` section.

Now let's go back to the homepage. Open ``http://node1.example.com/im`` with
your browser again. Try to sign in using your new credentials. If the astakos
menu appears and you can see your profile, then you have successfully setup
Astakos.

Let's continue to install Pithos+ now.


Installation of Pithos+ on node2
================================

To install pithos+, grab the packages from our repository (make sure  you made
the additions needed in your ``/etc/apt/sources.list`` file, as described
previously), by running:

.. code-block:: console

   # apt-get install snf-pithos-app

After successful installation of snf-pithos-app, make sure that also
snf-webproject has been installed (marked as "Recommended" package). Refer to
the "Installation of Astakos on node1" section, if you don't remember why this
should happen. Now, install the pithos web interface:

.. code-block:: console

   # apt-get install snf-pithos-webclient

This package provides the standalone pithos web client. The web client is the
web UI for pithos+ and will be accessible by clicking "pithos+" on the Astakos
interface's cloudbar, at the top of the Astakos homepage.

Configuration of Pithos+
========================

Conf Files
----------

After pithos+ is successfully installed, you will find the directory
``/etc/synnefo`` and some configuration files inside it, as you did in node1
after installation of astakos. Here, you will not have to change anything that
has to do with snf-common or snf-webproject. Everything is set at node1. You
only need to change settings that have to do with pithos+. Specifically:

Edit ``/etc/synnefo/20-snf-pithos-app-settings.conf``. There you need to set
only the two options:

.. code-block:: console

   PITHOS_BACKEND_DB_CONNECTION = 'postgresql://synnefo:example_passw0rd@node1.example.com:5432/snf_pithos'

   PITHOS_BACKEND_BLOCK_PATH = '/srv/pithos/data'

   PITHOS_AUTHENTICATION_URL = 'https://node1.example.com/im/authenticate'
   PITHOS_AUTHENTICATION_USERS = None

The ``PITHOS_BACKEND_DB_CONNECTION`` option tells to the pithos+ app where to
find the pithos+ backend database. Above we tell pithos+ that its database is
``snf_pithos`` at node1 and to connect as user ``synnefo`` with password
``example_passw0rd``.  All those settings where setup during node1's "Database
setup" section.

The ``PITHOS_BACKEND_BLOCK_PATH`` option tells to the pithos+ app where to find
the pithos+ backend data. Above we tell pithos+ to store its data under
``/srv/pithos/data``, which is visible by both nodes. We have already setup this
directory at node1's "Pithos+ data directory setup" section.

The ``PITHOS_AUTHENTICATION_URL`` option tells to the pithos+ app in which URI
is available the astakos authentication api. If not set, pithos+ tries to
authenticate using the ``PITHOS_AUTHENTICATION_USERS`` user pool.

Then we need to setup the web UI and connect it to astakos. To do so, edit
``/etc/synnefo/20-snf-pithos-webclient-settings.conf``:

.. code-block:: console

   PITHOS_UI_LOGIN_URL = "https://node1.example.com/im/login?next="
   PITHOS_UI_FEEDBACK_URL = "https://node1.example.com/im/feedback"

The ``PITHOS_UI_LOGIN_URL`` option tells the client where to redirect you, if
you are not logged in. The ``PITHOS_UI_FEEDBACK_URL`` option points at the
pithos+ feedback form. Astakos already provides a generic feedback form for all
services, so we use this one.

Then edit ``/etc/synnefo/20-snf-pithos-webclient-cloudbar.conf``, to connect the
pithos+ web UI with the astakos web UI (through the top cloudbar):

.. code-block:: console

   CLOUDBAR_LOCATION = 'https://node1.example.com/static/im/cloudbar/'
   PITHOS_UI_CLOUDBAR_ACTIVE_SERVICE = 'pithos'
   CLOUDBAR_SERVICES_URL = 'https://node1.example.com/im/get_services'
   CLOUDBAR_MENU_URL = 'https://node1.example.com/im/get_menu'

The ``CLOUDBAR_LOCATION`` tells the client where to find the astakos common
cloudbar.

The ``PITHOS_UI_CLOUDBAR_ACTIVE_SERVICE`` registers the client as a new service
served by astakos. It's name should be identical with the ``id`` name given at
the astakos' ``ASTAKOS_CLOUD_SERVICES`` variable. Note that at the Astakos "Conf
Files" section, we actually set the third item of the ``ASTAKOS_CLOUD_SERVICES``
list, to the dictionary: ``{ 'url':'https://nod...', 'name':'pithos+',
'id':'pithos }``. This item represents the pithos+ service. The ``id`` we set
there, is the ``id`` we want here.

The ``CLOUDBAR_SERVICES_URL`` and ``CLOUDBAR_MENU_URL`` options are used by the
pithos+ web client to get from astakos all the information needed to fill its
own cloudbar. So we put our astakos deployment urls there.

Servers Initialization
----------------------

After configuration is done, we initialize the servers on node2:

.. code-block:: console

   root@node2:~ # /etc/init.d/gunicorn restart
   root@node2:~ # /etc/init.d/apache2 restart

You have now finished the Pithos+ setup. Let's test it now.


Testing of Pithos+
==================

Open your browser and go to the Astakos homepage:

``http://node1.example.com/im``

Login, and you will see your profile page. Now, click the "pithos+" link on the
top black cloudbar. If everything was setup correctly, this will redirect you
to:

``https://node2.example.com/ui``

and you will see the blue interface of the Pithos+ application.  Click the
orange "Upload" button and upload your first file. If the file gets uploaded
successfully, then this is your first sign of a successful Pithos+ installation.
Go ahead and experiment with the interface to make sure everything works
correctly.

You can also use the Pithos+ clients to sync data from your Windows PC or MAC.

If you don't stumble on any problems, then you have successfully installed
Pithos+, which you can use as a standalone File Storage Service.

If you would like to do more, such as:

 * Spawning VMs
 * Spawning VMs from Images stored on Pithos+
 * Uploading your custom Images to Pithos+
 * Spawning VMs from those custom Images
 * Registering existing Pithos+ files as Images

please continue with the rest of the guide.

Installation of Cyclades (and Plankton) on node1
================================================

Installation of cyclades is a two step process:

1. install the external services (prerequisites) on which cyclades depends
2. install the synnefo software components associated with cyclades

Prerequisites
-------------
.. _cyclades-install-ganeti:

Ganeti installation
~~~~~~~~~~~~~~~~~~~

Synnefo requires a working Ganeti installation at the backend. Installation
of Ganeti is not covered by this document, please refer to
`ganeti documentation <http://docs.ganeti.org/ganeti/current/html>`_ for all the
gory details. A successful Ganeti installation concludes with a working
:ref:`GANETI-MASTER <GANETI_NODES>` and a number of :ref:`GANETI-NODEs <GANETI_NODES>`.

.. _cyclades-install-db:

Database
~~~~~~~~

Database installation is done as part of the
:ref:`snf-webproject <snf-webproject>` component.

.. _cyclades-install-rabbitmq:

RabbitMQ
~~~~~~~~

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
~~~~~~~~~~~~

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
~~~~~~~

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
~~~~~~~~~

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
------------------

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


Configuration of Cyclades (and Plankton)
========================================

This section targets the configuration of the prerequisites for cyclades,
and the configuration of the associated synnefo software components.

synnefo components
------------------

cyclades uses :ref:`snf-common <snf-common>` for settings.
Please refer to the configuration sections of
:ref:`snf-webproject <snf-webproject>`,
:ref:`snf-cyclades-app <snf-cyclades-app>`,
:ref:`snf-cyclades-gtools <snf-cyclades-gtools>` for more
information on their configuration.

Ganeti
~~~~~~

Set ``GANETI_NODES``, ``GANETI_MASTER_IP``, ``GANETI_CLUSTER_INFO`` based on
your :ref:`Ganeti installation <cyclades-install-ganeti>` and change the
`BACKEND_PREFIX_ID`` setting, using an custom ``PREFIX_ID``.

Database
~~~~~~~~

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
~~~~~~~~

Change ``RABBIT_*`` settings to match your :ref:`RabbitMQ setup
<cyclades-install-rabbitmq>`.

.. include:: ../../Changelog


Testing of Cyclades (and Plankton)
==================================


General Testing
===============


Notes
=====
