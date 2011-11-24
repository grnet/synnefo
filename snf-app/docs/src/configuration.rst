.. _configuration:

Configuration
=============


.. _settings-guide:

Customizing Synnefo settings
----------------------------

To ease up the configuration of the application Synnefo includes settings
defined in ``/etc/synnefo/*.conf`` files. The location can be altered by 
setting an enviromental variable named ``SYNNEFO_SETTINGS_DIR`` to the 
appropriate path, or by using the ``--settings-dir`` option of the
``synnefo-manage`` tool.

Synnefo package bundles a `Django` project with predefined common `settings` 
and `urls` set. The corresponding  ``manage.py`` for the bundled project is 
``synnefo-manage``. After the package installation the tool should be available 
as a command from your system's terminal. Due to this nature of `synnefo-manage`
it is possible to alter settings not only using ``.conf`` files but also by
providing a custom python module by using ``DJANGO_SETTINGS_MODULE``
evnironmental variable or ``--settings`` option of the tool.

.. seealso::
    https://docs.djangoproject.com/en/dev/topics/settings/

If you are using a custom settings module, you are strongly encouraged to
import the synnefo default settings prior to your customized ones e.g. :
    
.. code-block:: python
    
    from synnefo.settings import *

    CUSTOM_SETTING1 = "...."
    CUSTOM_SETTING2 = "...."

.. _database-configuration:

Database configuration
----------------------

Add the following to your custom :ref:`settings <settings-guide>`, depending on your choice
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


.. _database-initialization:

Database initialization
-----------------------

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

.. literalinclude:: ../../synnefo/db/fixtures/users.json

`download <../_static/users.json>`_

.. _additional-configuration:

.. include settings reference
.. include: settings.rst
