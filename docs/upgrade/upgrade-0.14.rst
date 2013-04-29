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

3.1 Set services and resources
------------------------------

Astakos and its resources should also get registered, so that they can
be known to the quota system.

Run::

    astakos-host$ snf-manage service-add astakos service_url api_url
    astakos-host$ snf-manage resource-export-astakos > astakos.json
    astakos-host$ snf-manage resource-import --json astakos.json
    astakos-host$ snf-manage resource-modify astakos.pending_app --limit <num>

The last command will set the limit of max pending project applications
per user. This replaces setting ASTAKOS_PENDING_APPLICATION_LIMIT.

In order to migrate the user-specific limits, run
(script: ``migrate_pending_app.py``)::

    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'
    from astakos.im.models import UserSetting, AstakosUserQuota, Resource

    SETTING = 'PENDING_APPLICATION_LIMIT'
    RESOURCE = 'astakos.pending_app'

    try:
        resource = Resource.objects.get(name=RESOURCE)
    except Resource.DoesNotExist:
        print "Resource 'astakos.pending_app' not found."
        exit()

    settings = UserSetting.objects.filter(setting=SETTING)
    for setting in settings:
        user = setting.user
        value = setting.value
        q, created = AstakosUserQuota.objects.get_or_create(
            user=user, resource=resource, capacity=value)
        if not created:
            print "Base quota already exists: %s %s" % (user.uuid, RESOURCE)
            continue
        print "Migrated base quota: %s %s %s" % (user.uuid, RESOURCE, value)

with::

    astakos-host$ python ./migrate_pending_app.py

followed by::

    astakos-host$ snf-manage reconcile-resources-astakos
