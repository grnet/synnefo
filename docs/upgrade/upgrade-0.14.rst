Upgrade to Synnefo v0.14
^^^^^^^^^^^^^^^^^^^^^^^^

The bulk of the upgrade to v0.14 is about resource and quota migrations.


.. warning::

    It is strongly suggested that you keep separate database backups
    for each service after the completion of each of step.

1. Bring web services down, backup databases
============================================

1. All web services must be brought down so that the database maintains a
   predictable and consistent state during the migration process::

    # service gunicorn stop
    # service snf-dispatcher stop
    # etc.

2. Backup databases for recovery to a pre-migration state.

3. Keep the database servers running during the migration process


2. Upgrade Synnefo and configure settings
=========================================

2.2 Sync and migrate Django DB
------------------------------

.. note::

   If you are asked about stale content types during the migration process,
   answer 'no' and let the migration finish.

::

    astakos-host$ snf-manage syncdb
    astakos-host$ snf-manage migrate quotaholder_app 0001 --fake
    astakos-host$ snf-manage migrate quotaholder_app
    astakos-host$ snf-manage migrate im

    cyclades-host$ snf-manage syncdb
    cyclades-host$ snf-manage migrate


3 Quota-related steps
=====================

Astakos and its resources should also get registered, so that they can
be known to the quota system.

Run::

    astakos-host$ snf-manage service-add astakos service_url api_url
    astakos-host$ snf-manage resource-export-astakos > astakos.json
    astakos-host$ snf-manage resource-import --json astakos.json

The limit on pending project applications is since 0.14 handled as an
Astakos resource, rather than a custom setting. In order to set this
limit (replacing setting ASTAKOS_PENDING_APPLICATION_LIMIT) run::

    astakos-host$ snf-manage resource-modify astakos.pending_app --limit <num>

To take into account the user-specific limits we need a data migration. The
following command populates the user-specific base quota for resource
``astakos.pending_app`` using the deprecated user setting::

    astakos-host$ astakos-migrate-0.14

Finally, Astakos needs to inform the quota system for the current number
of pending applications per user::

    astakos-host$ snf-manage reconcile-resources-astakos --fix

4 Change Astakos URIs in settings
=================================

In astakos-host edit ``/etc/synnefo/20-snf-astakos-app-cloudbar.conf`` and replace
the following lines:

.. code-block:: console

    CLOUDBAR_SERVICES_URL = 'https://node1.example.com/im/get_services'
    CLOUDBAR_MENU_URL = 'https://node1.example.com/im/get_menu'

with:

.. code-block:: console

    CLOUDBAR_SERVICES_URL = 'https://node1.example.com/astakos/api/get_services'
    CLOUDBAR_MENU_URL = 'https://node1.example.com/astakos/api/get_menu'

|

Also in pithos-host edit ``/etc/synnefo/20-snf-pithos-webclient-cloudbar.conf``
and the following lines:

.. code-block:: console

    CLOUDBAR_SERVICES_URL = 'https://node1.example.com/im/get_services'
    CLOUDBAR_MENU_URL = 'https://node1.example.com/im/get_menu'

with:

.. code-block:: console

    CLOUDBAR_SERVICES_URL = 'https://node1.example.com/astakos/api/get_services'
    CLOUDBAR_MENU_URL = 'https://node1.example.com/astakos/api/get_menu'

|

Finally in cyclades-node edit ``/etc/synnefo/20-snf-cyclades-app-cloudbar.conf``
and replace the following lines:

.. code-block:: console

   CLOUDBAR_SERVICES_URL = 'https://node1.example.com/im/get_services'
   CLOUDBAR_MENU_URL = 'https://account.node1.example.com/im/get_menu'

with:

.. code-block:: console

   CLOUDBAR_SERVICES_URL = 'https://node1.example.com/astakos/api/get_services'
   CLOUDBAR_MENU_URL = 'https://account.node1.example.com/astakos/api/get_menu'
