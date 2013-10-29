Upgrade to Synnefo v0.15
^^^^^^^^^^^^^^^^^^^^^^^^

The upgrade to v0.15 consists in the following steps:

1. Bring down services and backup databases.

2. Upgrade packages, migrate the databases and configure settings.

3. Re-register components and services in astakos.

4. Bring up all services.

.. warning::

    It is strongly suggested that you keep separate database backups
    for each service after the completion of each step.

1. Bring web services down, backup databases
============================================

1. All web services must be brought down so that the database maintains a
   predictable and consistent state during the migration process::

    $ service gunicorn stop
    $ service snf-dispatcher stop
    $ service snf-ganeti-eventd stop

2. Backup databases for recovery to a pre-migration state.

3. Keep the database servers running during the migration process.


2. Upgrade Synnefo and configure settings
=========================================

2.1 Install the new versions of packages
----------------------------------------

::

    astakos.host$ apt-get install \
                            python-objpool \
                            snf-common \
                            python-astakosclient \
                            snf-django-lib \
                            snf-webproject \
                            snf-branding \
                            snf-astakos-app

    cyclades.host$ apt-get install \
                            python-objpool \
                            snf-common \
                            python-astakosclient \
                            snf-django-lib \
                            snf-webproject \
                            snf-branding \
                            snf-pithos-backend \
                            snf-cyclades-app

    pithos.host$ apt-get install \
                            python-objpool \
                            snf-common \
                            python-astakosclient \
                            snf-django-lib \
                            snf-webproject \
                            snf-branding \
                            snf-pithos-backend \
                            snf-pithos-app \
                            snf-pithos-webclient

    ganeti.node$ apt-get install \
                            python-objpool \
                            snf-common \
                            snf-cyclades-gtools \
                            snf-pithos-backend

.. note::

   Make sure `snf-webproject' has the same version with snf-common

.. note::

    Installing the packages will cause services to start. Make sure you bring
    them down again (at least ``gunicorn``, ``snf-dispatcher``)

2.2 Sync and migrate the database
---------------------------------

.. note::

   If you are asked about stale content types during the migration process,
   answer 'no' and let the migration finish.

::

    astakos-host$ snf-manage syncdb
    astakos-host$ snf-manage migrate

    cyclades-host$ snf-manage syncdb
    cyclades-host$ snf-manage migrate

    pithos-host$ pithos-migrate upgrade head

2.3 Update configuration files
------------------------------

The ``ASTAKOS_BASE_URL`` setting has been replaced (both in Cyclades and
Pithos services) with the ``ASTAKOS_AUTH_URL`` setting.

For Cyclades service we have to change the ``20-snf-cyclades-app-api.conf``
file, remove the ``ASTAKOS_BASE_URL`` setting and replace it with
``ASTAKOS_AUTH_URL``. Typically it is sufficient to add ``/identity/v2.0``
at the end of base url to get the auth url. For example if base url had the
value of 'https://accounts.example.synnefo.org/' then the ``ASTAKOS_AUTH_URL``
setting will have the value of
'https://accounts.example.synnefo.org/identity/v2.0'.

For Pithos service we have to change the ``20-snf-pithos-app-settings.conf``
file in the same way as above.

3. Re-register components and services in astakos
=================================================

Component registration has changed; you will thus need to repeat the
process. On the astakos node, run::

    astakos-host$ snf-component-register

This will detect that the Synnefo components are already registered and ask
to re-register. Answer positively. You need to enter the base URL and the UI
URL for each component, just like during the initial registration.

4. Bring all services up
========================

After the upgrade is finished, we bring up all services:

.. code-block:: console

    astakos.host  # service gunicorn start
    cyclades.host # service gunicorn start
    pithos.host   # service gunicorn start

    cyclades.host # service snf-dispatcher start
