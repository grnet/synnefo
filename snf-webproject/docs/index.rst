.. _snf-webproject:

Component snf-webproject
========================

synnefo component :ref:`snf-webproject <snf-webproject>` defines a Django 
project in which the various other synnefo components
(:ref:`snf-cyclades-app <snf-cyclades-app>`,
:ref:`snf-pithos-app <snf-pithos-app>`, etc.) may run.

It provides a standard mechanism for every synnefo software component to modify
the list of Django apps to be executed inside the project (``INSTALLED_APPS``),
modify the list of middleware classes (``MIDDLEWARE_CLASSES``) and add its own
URL patterns.

.. todo:: Document snf-webproject facilities for developers

Package installation
--------------------

.. todo:: kpap: verify instructions for installation from source.

Use ``pip`` to install the latest version of the package from source,
or request a specific version as ``snf-webproject==x.y.z``.

.. code-block:: console

   pip install snf-webproject -f https://www.synnefo.org/packages/pypi

On Debian Squeeze, install the ``snf-webproject`` Debian package.

Package configuration
---------------------

Database
********

You need to create a database for use by the Django project,
then configure your custom :ref:`snf-common <snf-common>` settings,
according to your choice of DB.

DB creation
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
   in your custom settings, e.g., in :file:`/etc/synnefo/10-database.conf`:
       
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

DB driver
`````````

Depending on your DB of choice, install one of the following:

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

DB settings
```````````

Add the following to your custom :ref:`snf-common <snf-common>`, depending on
your choice of DB:

SQLite
~~~~~~
.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/path/to/synnefo.db'
        }
    }

.. warning:: ``NAME`` must be an absolute path to the sqlite3 database file


MySQL
~~~~~

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
~~~~~~~~~~

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

.. code-block:: console

    $ snf-manage sql db

Web server
**********

You need to configure your webserver to serve static files and relay
requests to :ref:`snf-webproject <snf-webproject>`.


.. static_files::
Static files
````````````

:ref:`snf-webproject <snf-webproject>` provides a helper mechanism to avoid tedious
tasks involving the collection and deployment of installed applications static
files (js/css/images etc.). The mechanism tries to mimic the ``staticfiles``
application included in ``Django>=1.3`` but its far less robust and adequate
regarding its capabilities. When ``Django>=1.3`` become available as a package 
for the stable release of ``Debian``, the current mechanism will get wiped off
to be replaced by the ``staticfiles`` contrib application.

The current mechanism provides a tool to collect the static files of the synnefo
components installed and enabled in your system and an automatic way of serving
those files directly from your django project. Be concerned that the latter is
for debugging pupropses only since serving static files from your django project
is considered as a bad practice.

Each django based synnefo component informs webproject mechanism for the static 
files it contains using the ``synnefo.web_static`` entry point which should point
to a dict containing a map of a python module and a namespace for the url under
which the files will be served from. As an example of use we can see how 
snf-cyclades-app informs webproject for the static files of ui and admin applications.

in ``setup.py``::
    
    ...
    entry_points = {
     ...
     'synnefo': [
         ...
         'web_static = synnefo.app_settings:synnefo_static_files',
         ...
         ]
      },
    ...

and inside ``synnefo/app_settings/__init__.py``::

    synnefo_static_files = {
        'synnefo.ui': 'ui',
        'synnefo.admin': 'admin',
    }


Collecting static files
^^^^^^^^^^^^^^^^^^^^^^^

* Choose an appropriate path (e.g. :file:`/var/lib/synnefo/static/`) from which
  your web server will serve all static files (js/css) required by the synnefo
  web frontend to run.
* Change the ``MEDIA_ROOT`` value in your settings (see :ref:`snf-common
  <snf-common>`) to point to that directory.
* Create symlinks to the static files of all synnefo webapp components
  inside the chosen directory, by running:

.. code-block:: console

    $ snf-manage link_static


Serving static files
^^^^^^^^^^^^^^^^^^^^

By default will serve the static files if ``DEBUG`` setting is set to True.
You can override this behaviour by explicitly setting the 
``WEBPROJECT_SERVE_STATIC`` to True or False in your settings files.


Apache
``````

.. todo:: document Apache configuration

nginx
`````
This section describes a sample nginx configuration which uses FastCGI
to relay requests to synnefo.

First, use a distribution-specific mechanism (e.g., APT) to install nginx:

.. code-block:: console

   # apt-get install nginx

Then activate the following nginx configuration file by placing it under
:file:`/etc/nginx/sites-available` and symlinking under
:file:`/etc/nginx/sites-enabled`:

.. literalinclude:: ../_static/synnefo.nginx.conf

.. todo:: fix the location of the configuration file

`download <../_static/synnefo.nginx.conf>`_

Once nginx is configured, run the FastCGI server to receive incoming requests
from nginx. This requires installation of package ``flup``:

.. code-block:: console

    # apt-get install flup
    $ snf-manage runfcgi host=127.0.0.1 port=8015


For developers
--------------

Available entry points
^^^^^^^^^^^^^^^^^^^^^^

web_apps
````````
Extends INSTALLED_APPS django project setting.

Example::
    
    # myapp/synnefo_settings.py
    # synnefo_settings and variable name is arbitary
    my_app_web_apps = ['myapp', 'south', 'django.contrib.sessions']
    
    # another more complex configuration where we need our app to be placed
    # before django.contrib.admin app because it overrides some of the admin
    # templates used by admin app views
    my_app_web_apps = [{'before':'django.contrib.admin', 'insert':'myapp'}, 'south']

    # setup.py
    entry_points = {
        'synnefo': ['web_apps = myapp.synnefo_settings:my_app_web_apps']
    }


web_middleware
``````````````
Extends MIDDLEWARE_CLASSES django setting.


web_static
``````````
Extends STATIC_FILES setting (see `static_files`_).


web_context_processors
``````````````````````
Extends TEMPLATE_CONTEXT_PROCESSORS django setting.


loggers
```````
Extends `snf-common`_ LOGGING_SETUP['loggers'] setting.


urls
````
Extends django project urls. Accepts a urlpatterns variable. The urls defined
in this variable will be used to extend the django project urls.
