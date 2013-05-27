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


2.3 Configure Base URL settings for all services
------------------------------------------------

In order to make all services' URLs configurable and discoverable from
a single endpoint in Astakos through the Openstack Keystone API,
every service has a ``XXXXX_BASE_URL`` setting, or it's old corresponding
setting was renamed to this. Therefore:

* Rename ``ASTAKOS_URL`` setting to ``ASTAKOS_BASE_URL``
  everywhere in your settings, in all nodes and all config files.
  This must point to the top-level Astakos URL.

* In Cyclades settings, rename the ``APP_INSTALL_URL`` setting
  to ``CYCLADES_BASE_URL``. If no such setting has been configured,
  you must set it. It must point to the top-level Cyclades URL.

* In Pithos settings, introduce a ``PITHOS_BASE_URL`` setting.
  It must point to the top-level Pithos URL.

3 Register astakos service and migrate quota
============================================

You need to register Astakos as a service. The following command will ask
you to provide the service URL (to appear in the Cloudbar) as well as its
API URL. It will also automatically register the resource definitions
offered by astakos.

Run::

    astakos-host$ snf-register-services astakos

.. note::

   This command is equivalent to running:

   .. code-block:: console
     astakos-host$ snf-manage service-add astakos service_url api_url
     astakos-host$ snf-manage resource-export-astakos > astakos.json
     astakos-host$ snf-manage resource-import --json astakos.json


The limit on pending project applications is since 0.14 handled as an
Astakos resource, rather than a custom setting. Command::

    astakos-host$ astakos-migrate-0.14

will prompt you to set this limit (replacing setting
ASTAKOS_PENDING_APPLICATION_LIMIT) and then automatically migrate the
user-specific base quota for the new resource ``astakos.pending_app`` using
the deprecated user setting.
