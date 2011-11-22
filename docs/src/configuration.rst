Configuration
=============

Customizing Synnefo settings
----------------------------

Synnefo package bundles a `Django` project with predefined common `settings` 
and `urls` set. The corresponding `Django` ``manage.py`` for the bundled project is 
``synnefo-manage`` which after the package installation should be available in
your system ``PATH``.

To ease up the configuration of the application Synnefo includes settings
defined in ``/etc/synnefo/*.conf`` files.

Database
--------

Add the following to your custom settings.py, depending on your choice
of DB:

SQLite
******
.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/path/to/synnefo.db'
        }
    }

.. warning:: `NAME` must be an absolute path to the sqlite3 database file

MySQL
*****
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
**********
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
print out DDL statements. It should not fail::

    $ synnefo-manage sql db

You need to initialize the Synnefo DB::

    $ synnefo-manage syncdb
    $ synnefo-manage migrate

and load fixtures {users,flavors,images}, 
which make the API usable by end users by defining a sample set of users, 
hardware configurations (flavors) and OS images::

    $ synnefo-manage loaddata /path/to/users.json
    $ synnefo-manage loaddata flavors
    $ synnefo-manage loaddata images

.. warning:: 
    Be sure to load a custom users.json and select a unique token 
    for each of the initial and any other users defined in this file. 
    **DO NOT LEAVE THE SAMPLE AUTHENTICATION TOKENS** enabled in deployed
    configurations.

sample users.json file:

.. code-block::
    .. include:: ../../synnefo/db/fixtures/users.json


Additional configuration
************************

Installation of the Synnefo dispatcher, ``synnefo-dispatcher``:
The logic dispatcher is part of the Synnefo Django project and must run
on LOGIC nodes.

The dispatcher retrieves messages from the queue and calls the appropriate
handler function as defined in the queue configuration in `/etc/synnefo/*.conf'
files.

The default configuration should work directly without any modifications.

For the time being The dispatcher must be run by hand::

  $ synnefo-dispatcher

The dispatcher should run in at least 2 instances to ensure high
(actually, increased) availability.

