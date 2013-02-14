.. _i-webproject:

Synnefo
-------

:ref:`synnefo <i-synnefo>` ||
:ref:`ns <i-ns>` ||
:ref:`apt <i-apt>` ||
:ref:`mq <i-mq>` ||
:ref:`db <i-db>` ||
:ref:`gunicorn <i-gunicorn>` ||
:ref:`apache <i-apache>` ||
webproject ||
:ref:`astakos <i-astakos>` ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

Webproject Setup
++++++++++++++++

The following apply to  ``astakos``, ``pithos``, ``cyclades`` and ``cms`` nodes.

First install:

.. code-block:: console

   # apt-get install python-psycopg2
   # apt-get install snf-webproject

In `/etc/synnefo/snf-webproject.conf` add:

.. code-block:: console

   from synnefo.lib.db.pooled_psycopg2 import monkey_patch_psycopg2
   monkey_patch_psycopg2()

   from synnefo.lib.db.psyco_gevent import make_psycopg_green
   make_psycopg_green()

   DATABASES = {
    'default': {
        # 'postgresql_psycopg2', 'postgresql','mysql', 'sqlite3' or 'oracle'
        'ENGINE': 'postgresql_psycopg2',
        'OPTIONS': {'synnefo_poolsize': 8},
         # ATTENTION: This *must* be the absolute path if using sqlite3.
         # See: http://docs.djangoproject.com/en/dev/ref/settings/#name
        'NAME': 'snf_apps',
        'USER': 'synnefo',                      # Not used with sqlite3.
        'PASSWORD': 'examle_passw0rd',          # Not used with sqlite3.
        # Set to empty string for localhost. Not used with sqlite3.
        'HOST': 'db.example.com',
        # Set to empty string for default. Not used with sqlite3.
        'PORT': '5432',
    }
   }

   USE_X_FORWARDED_HOST = True

   SECRET_KEY = 'sy6)mw6a7x%n)-example_secret_key#zzk4jo6f2=uqu!1o%)'

All the above enables pooling (of connections) and greenlet context.


Test your Setup:
++++++++++++++++
