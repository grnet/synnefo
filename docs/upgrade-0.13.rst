Upgrade to Synnefo v0.13
^^^^^^^^^^^^^^^^^^^^^^^^

The bulk of the upgrade to v0.13 is about user and quota migrations.
In summary, the migration process has 3 steps:

1. Run some commands and scripts to diagnose and extract some migration data
   while the OLD code is running, and BEFORE any changes are made.

2. Bring down services, upgrade packages, configure services, and perform
   django database migrations. These migrations do not need any interaction
   between services.

3. Initialize the Astakos quota system and bring the Astakos service up, since
   it will be needed during a second-phase of UUID and quota migrations, that
   also uses data extracted from step 1.


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


2. Prepare astakos user migration to case insensitive emails
============================================================

It is possible that two or more users have been registered with emails that
differ only in the case of its letters.  There can only be one of those
accounts after the migration, so the rest must be deleted.

Note that even if the users are deleted in Astakos, there still are duplicate
entries in Cyclades and Pithos.  For each service we need to reduce those
multiple accounts into one, either merging them together, or deleting and
discarding data from all but one.

.. _find_duplicate_emails:

2.1 Find duplicate email entries in Astakos
-------------------------------------------
(script: ``find_astakos_users_with_conflicting_emails.py``)::

    astakos-host$ cat << EOF > find_astakos_users_with_conflicting_emails.py
    #!/usr/bin/env python
    import os
    import sys

    os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'

    import astakos
    from astakos.im.models import AstakosUser as A


    def user_filter(user):
        return A.objects.filter(email__iexact=user.email).count() > 1

    all_users = list(A.objects.all())
    userlist = [(str(u.pk) + ': ' + str(u.email) + ' (' + str(u.is_active) + ', ' +
                 str(u.date_joined) + ')') for u in filter(user_filter, all_users)]

    sys.stderr.write("id email (is_active, creation date)\n")
    print "\n".join(userlist)
    EOF

    astakos-host$ python ./find_astakos_users_with_conflicting_emails.py

.. _remove_astakos_duplicate:

2.1 Remove duplicate users in Astakos by their id
-------------------------------------------------
(script: ``delete_astakos_users.py``)::

    astakos-host$ cat << EOF > delete_astakos_users.py
    #!/usr/bin/env python

    import os
    import sys
    from time import sleep

    os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'

    import astakos
    from astakos.im.models import AstakosUser as A


    def user_filter(user):
        return A.objects.filter(email__iexact=user.email).count() > 1

    argv = sys.argv
    argc = len(sys.argv)

    if argc < 2:
        print "Usage: ./delete_astakos_users.py <id>..."
        raise SystemExit()

    id_list = [int(x) for x in argv[1:]]

    print ""
    print "This will permanently delete the following users:\n"
    print "id  email (is_active, creation date)"
    print "--  --------------------------------"

    users = A.objects.filter(id__in=id_list)
    for user in users:
        print "%s: %s (%s, %s)" % (user.id, user.email, user.is_active,
                                   user.date_joined)

    print "\nExecute? (yes/no): ",
    line = raw_input().rstrip()
    if line != 'yes':
        print "\nCancelled"
        raise SystemExit()

    print "\nConfirmed."
    sleep(2)
    for user in users:
        print "deleting %s: %s" % (user.id, user.email)
        user.delete()

    EOF

    astakos-host$ python ./delete_astakos_users.py 30 40

.. warning::

    After deleting users with the ``delete_astakos_users.py`` script,
    check again with ``find_astakos_users_with_conflicting_emails.py``
    (as in :ref:`find_duplicate_emails`)
    to make sure that no duplicate email conflicts remain.


3. Upgrade Synnefo and configure settings
=========================================

3.1 Install the new versions of packages
----------------------------------------

::

    astakos.host$ apt-get install \
                            kamaki \
                            snf-common \
                            snf-webproject \
                            snf-quotaholder-app \
                            snf-astakos-app \


    cyclades.host$ apt-get install \
                            kamaki \
                            snf-common \
                            snf-webproject
                            snf-pithos-backend \
                            snf-cyclades-app \

                           
    pithos.host$ apt-get install \
                            kamaki \
                            snf-common \
                            snf-webproject
                            snf-pithos-backend \
                            snf-pithos-app \
                            snf-pithos-webclient \


    ganeti.node$ apt-get install \
                            kamaki \
                            snf-common \
                            snf-cyclades-gtools \
                            snf-pithos-backend \

.. note::

    Installing the packages will cause services to start. Make sure you bring
    them down again (at least ``gunicorn``, ``snf-dispatcher``)

3.2 Sync and migrate Django DB
------------------------------

.. note::

   If you are asked about stale content types during the migration process,
   answer 'no' and let the migration finish.

::

    astakos-host$ snf-manage syncdb
    astakos-host$ snf-manage migrate

    cyclades-host$ snf-manage syncdb
    cyclades-host$ snf-manage migrate

.. note::

    After the migration, Astakos has created uuids for all users,
    and has set the uuid as the public identifier of a user.
    This uuid is to be used both at other services (Cyclades, Pithos)
    and at the clientside (kamaki client settings).

    Duplicate-email users have been deleted earlier in
    :ref:`remove_astakos_duplicate`

3.3 Setup quota settings for all services
-----------------------------------------

Generally:

::

    # Service       Setting                       Value
    # quotaholder:  QUOTAHOLDER_TOKEN          = <random string>

    # astakos:      ASTAKOS_QUOTAHOLDER_TOKEN  = <the same random string>
    # astakos:      ASTAKOS_QUOTAHOLDER_URL    = https://quotaholder.host/quotaholder/v

    # cyclades:     CYCLADES_QUOTAHOLDER_TOKEN = <the same random string>
    # cyclades:     CYCLADES_QUOTAHOLDER_URL   = https://quotaholder.host/quotaholder/v
    # cyclades:     CYCLADES_USE_QUOTAHOLDER   = True


    # pithos:       PITHOS_QUOTAHOLDER_TOKEN   = <the same random string>
    # pithos:       PITHOS_QUOTAHOLDER_URL     = https://quotaholder.host/quotaholder/v
    # pithos:       PITHOS_USE_QUOTAHOLDER     = True
    # All services must match the quotaholder token and url configured for quotaholder.

Specifically:

On the Astakos host, edit ``/etc/synnefo/20-snf-astakos-app-settings.conf``:

::

    QUOTAHOLDER_TOKEN = 'aExampleTokenJbFm12w'
    ASTAKOS_QUOTAHOLDER_TOKEN = 'aExampleTokenJbFm12w'
    ASTAKOS_QUOTAHOLDER_URL = 'https://accounts.example.synnefo.org/quotaholder/v'

On the Cyclades host, edit ``/etc/synnefo/20-snf-cyclades-app-quotas.conf``:

::

    CYCLADES_USE_QUOTAHOLDER = True
    CYCLADES_QUOTAHOLDER_URL = 'https://accounts.example.synnefo.org/quotaholder/v'
    CYCLADES_QUOTAHOLDER_TOKEN = 'aExampleTokenJbFm12w'

On the Pithos host, edit ``/etc/synnefo/20-snf-pithos-app-settings.conf``:

::

    PITHOS_QUOTAHOLDER_URL = 'https://accounts.example.synnefo.org/quotaholder/v'
    PITHOS_QUOTAHOLDER_TOKEN = 'aExampleTokenJbFm12w'
    PITHOS_USE_QUOTAHOLDER = False # will set to True after migration

.. note::

    During the migration it must be set, ``PITHOS_USE_QUOTAHOLDER = False``.
    Set to ``True`` once the migration is over.

3.4 Setup astakos
-----------------

- **Remove** this redirection from astakos front-end web server ::

        RewriteRule ^/login(.*) /im/login/redirect$1 [PT,NE]

    (see `<http://docs.dev.grnet.gr/synnefo/latest/quick-install-admin-guide.html#apache2-setup>`_)

- Enable users to change their contact email. Edit
``/etc/synnefo/20-snf-astakos-app-settings.conf`` ::

    ASTAKOS_EMAILCHANGE_ENABLED = True

- Rename the following (Astakos-specific) setting::

    ASTAKOS_DEFAULT_FROM_EMAIL
  
  to this (Django-specific) name::

    SERVER_EMAIL

- Instead of using the following (Astakos-specific) setting::

    ASTAKOS_DEFAULT_ADMIN_EMAIL

  include one or more entries in this (Django-specific) setting::

    ADMINS = (
        ('Joe Doe', 'doe@example.net'),
        ('Mary Jean', 'mary@example.net'),
    ) 

.. note::

    The ``SERVER_EMAIL`` and ``ADMINS`` settings are Django-specific.
    As such they will be the shared for any two (or more) services that happen
    to be collocated within the same application server (e.g. astakos &
    cyclades within the same gunicorn)

3.5 Setup Cyclades
------------------

- Run on the Astakos host ::

    # snf-manage service-list

- Set the Cyclades service token in
  ``/etc/synnefo/20-snf-cyclades-app-api.conf`` ::

    CYCLADES_ASTAKOS_SERVICE_TOKEN = 'asfasdf_CycladesServiceToken_iknl'

- Since version 0.13, Synnefo uses **VMAPI** in order to prevent sensitive data
  needed by 'snf-image' to be stored in Ganeti configuration (e.g. VM
  password). This is achieved by storing all sensitive information to a CACHE
  backend and exporting it via VMAPI. The cache entries are invalidated after
  the first request. Synnefo uses **memcached** as a django cache backend.
  To install, run on the Cyclades host::

        apt-get install memcached
        apt-get install python-memcache

  You will also need to configure Cyclades to use the memcached cache backend.
  Namely, you need to set IP address and port of the memcached daemon, and the
  default timeout (seconds tha value is stored in the cache). Edit
  ``/etc/synnefo/20-snf-cyclades-app-vmapi.conf`` ::

    VMAPI_CACHE_BACKEND = "memcached://127.0.0.1:11211/?timeout=3600"


  Finally, set the BASE_URL for the VMAPI, which is actually the base URL of
  Cyclades, again in ``/etc/synnefo/20-snf-cyclades-app-vmapi.conf``. Make sure
  the domain is exaclty the same, so that no re-directs happen ::

    VMAPI_BASE_URL = "https://cyclades.example.synnefo.org"

  .. note::

    - These settings are needed in all Cyclades workers.

    - VMAPI_CACHE_BACKEND just overrides django's CACHE_BACKEND setting

    - memcached must be reachable from all Cyclades workers.

    - For more information about configuring django to use memcached:
      https://docs.djangoproject.com/en/1.2/topics/cache

3.6 Setup Pithos
----------------

- Pithos forwards user catalog services to Astakos so that web clients may
  access them for uuid-displayname translations. Edit on the Pithos host
  ``/etc/synnefo/20-snf-pithos-app-settings.conf`` ::

    PITHOS_USER_CATALOG_URL    = https://accounts.example.synnefo.org/user_catalogs/
    PITHOS_USER_FEEDBACK_URL   = https://accounts.example.synnefo.org/feedback/
    PITHOS_USER_LOGIN_URL      = https://accounts.example.synnefo.org/login/
    #PITHOS_PROXY_USER_SERVICES = True # Set False if astakos & pithos are on the same host


4. Start astakos and quota services
===================================
.. warning::

    To ensure consistency, prevent public access to astakos during migrations.
    This can be done via firewall or webserver access control.

Start (or restart, if running) the webserver and gunicorn on the Astakos host.
E.g.::

    # service apache2 start
    # service gunicorn start

.. _astakos-load-resources:

5. Load resource definitions into Astakos
=========================================

First, set the corresponding values on the following dict in
``/etc/synnefo/20-snf-astakos-app-settings.conf`` ::

    # Set the cloud service properties
    ASTAKOS_SERVICES = {
        'cyclades': {
    #        # Specifying the key 'url' will overwrite it.
    #        # Use this to (re)set service URL.
    #        'url': 'https://cyclades.example.synnefo.org/ui/',
    #        # order services in listings, cloudbar, etc.
    #        'order' : 1
            'resources': [{
                'name': 'disk',
                'group': 'compute',
                'uplimit': 30*1024*1024*1024,
                'unit': 'bytes',
                'desc': 'Virtual machine disk size'
                }, {
                'name': 'cpu',
                'group': 'compute',
                'uplimit': 6,
                'desc': 'Number of virtual machine processors'
                }, {
                'name': 'ram',
                'group': 'compute',
                'uplimit': 6*1024*1024*1024,
                'unit': 'bytes',
                'desc': 'Virtual machines'
                }, {
                'name': 'vm',
                'group': 'compute',
                'uplimit': 2,
                'desc': 'Number of virtual machines'
                }, {
                'name': 'network.private',
                'group': 'network',
                'uplimit': 1,
                'desc': 'Private networks'
                }
            ]
        },
        'pithos+': {
    #        # Use this to (re)set service URL.
    #        'url': 'https://pithos.example.synnefo.org/ui/',
    #        # order services in listings, cloudbar, etc.
    #        'order' : 2
            'resources':[{
                'name': 'diskspace',
                'group': 'storage',
                'uplimit': 5*1024*1024*1024,
                'unit': 'bytes',
                'desc': 'Pithos account diskspace'
                }]
        }
    }

.. note::

    The name of the Pithos service is ``pithos+``.
    If you have named your pithos service ``pithos``, without ``+``,
    then you must rename it::

        $ snf-manage service-list | grep pithos # find service id
        $ snf-manage service-update --name='pithos+' <service id> 

Then, configure and load the available resources per service
and associated default limits into Astakos. On the Astakos host run ::

     # snf-manage astakos-init --load-service-resources


.. note::

    Before v0.13, only `cyclades.vm`, `cyclades.network.private`,
    and `pithos+.diskspace` existed (not with these names,
    there were per-service settings).
    However, limits to the new resources must also be set.

    If the intetion is to keep a resource unlimited, (counting on that VM
    creation will be limited by other resources' limit) it is best to calculate
    a value that is too large to be reached because of other limits (and
    available flavours), but not much larger than needed because this might
    confuse users who do not readily understand that multiple limits apply and
    flavors are limited.


6. Migrate Services user names to uuids
=======================================


6.1 Double-check cyclades before user case/uuid migration
---------------------------------------------------------

::

    cyclades.host$ snf-manage cyclades-astakos-migrate-013 --validate

Duplicate user found?

- either *merge* (merge will merge all resources to one user)::

    cyclades.host$ snf-manage cyclades-astakos-migrate-013 --merge-user=kpap@grnet.gr

- or *delete* ::

    cyclades.host$ snf-manage cyclades-astakos-migrate-013 --delete-user=KPap@grnet.gr
    # (only KPap will be deleted not kpap)

6.2 Double-check pithos before user case/uuid migration
---------------------------------------------------------

::

    pithos.host$ snf-manage pithos-manage-accounts --list-duplicate

Duplicate user found?

If you want to migrate files first:

- *merge* (merge will merge all resources to one user)::

    pithos.host$ snf-manage pithos-manage-accounts --merge-accounts --src-account=SPapagian@grnet.gr --dest-account=spapagian@grnet.gr
    # (SPapagian@grnet.gr's contents will be merged into spapagian@grnet.gr, but SPapagian@grnet.gr account will still exist)

- and then *delete* ::

    pithos.host$ snf-manage pithos-manage-accounts --delete-account=SPapagian@grnet.gr
    # (only SPapagian@grnet.gr will be deleted not spapagian@grnet.gr)

If you do *NOT* want to migrate files just run the second step and delete
the duplicate account.

6.3 Migrate Cyclades users (email case/uuid)
--------------------------------------------

::

    cyclades.host$ snf-manage cyclades-astakos-migrate-013 --migrate-users

- if invalid usernames are found, verify that they do not exist in astakos::

    astakos.host$ snf-manage user-list

- if no user exists::

    cyclades.host$ snf-manage cyclades-astakos-migrate-013 --delete-user=<userid>

Finally, if you have set manually quotas for specific users inside
``/etc/synnefo/20-snf-cyclades-app-api.conf`` (in ``VMS_USER_QUOTA``,
``NETWORKS_USER_QUOTA`` make sure to update them so that:

1. There are no double entries wrt case sensitivity
2. Replace all user email addresses with the corresponding UUIDs

To find the UUIDs for step 2 run on the Astakos host ::

     # snf-manage user-list

6.4 Migrate Pithos user names
-----------------------------

Check if alembic has not been initialized ::

    pithos.host$ pithos-migrate current

- If alembic current is None (e.g. okeanos.io) ::

    pithos.host$ pithos-migrate stamp 3dd56e750a3

Then, migrate pithos account name to uuid::

    pithos.host$ pithos-migrate upgrade head

Finally, set this setting to ``True``::

    PITHOS_USE_QUOTAHOLDER = True


7. Migrate old quota limits
===========================

7.1 Migrate Pithos quota limits to Astakos
------------------------------------------

Migrate from pithos native to astakos/quotaholder.
This requires a file to be transfered from Cyclades to Astakos::

    pithos.host$ snf-manage pithos-export-quota --location=pithos-quota.txt
    pithos.host$ scp pithos-quota.txt astakos.host:
    astakos.host$ snf-manage user-set-initial-quota pithos-quota.txt

.. _export-quota-note:

.. note::

    `pithos-export-quota` will only export quotas that are not equal to the
    defaults in Pithos. Therefore, it is possible to both change or maintain
    the default quotas across the migration. To maintain quotas the new default
    pithos+.diskpace limit in Astakos must be equal to the (old) default quota
    limit in Pithos. Change either one of them make them equal.

    see :ref:`astakos-load-resources` on how to set the (new) default quotas in Astakos.

7.2 Migrate Cyclades quota limits to Astakos
--------------------------------------------

::

    cyclades.host$ snf-manage cyclades-export-quota --location=cyclades-quota.txt
    cyclades.host$ scp cyclades-quota.txt astakos.host:
    astakos.host$ snf-manage user-set-initial-quota cyclades-quota.txt

`cyclades-export-quota` will only export quotas that are not equal to the defaults.
See :ref:`note above <export-quota-note>`.

8. Enforce the new quota limits migrated to Astakos
===================================================
The following should report all users not having quota limits set
because the effective quota database has not been initialized yet. ::

    astakos.host$ snf-manage astakos-quota --verify

Initialize the effective quota database::

    astakos.host$ snf-manage astakos-quota --sync

This procedure may be used to verify and re-synchronize the effective quota
database with the quota limits that are derived from policies in Astakos
(initial quotas, project memberships, etc.)

9. Initialize resource usage
============================

The effective quota database (quotaholder) has just been initialized and knows
nothing of the current resource usage. Therefore, each service must send it in.

9.1 Initialize Pithos resource usage
------------------------------------

::

    pithos.host$ snf-manage pithos-reset-usage

9.2 Initialize Cyclades resource usage
--------------------------------------

::

    cyclades.host$ snf-manage cyclades-reset-usage

10. Install periodic project maintainance checks
================================================
In order to detect and effect project expiration,
a management command has to be run periodically
(depending on the required granularity, e.g. once a day/hour)::

    astakos.host$ snf-manage project-control --terminate-expired

A list of expired projects can be extracted with::

    astakos.host$ snf-manage project-control --list-expired


11. Restart all services
========================

Start (or restart, if running) all Synnefo services on all hosts.

::

    # service gunicorn restart
    # service snf-dispatcher restart
    # etc.
