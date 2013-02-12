Upgrade to Synnefo v0.13
^^^^^^^^^^^^^^^^^^^^^^^^

The bulk of the upgrade to v0.13 is about user and quota migrations.
In summary, the migration process has 3 steps:

1. Run some commands and scripts to diagnose and extract some migration data
   while the OLD code is running, and BEFORE any changes are made.

2. Bring down services, upgrade packages, configure services, and perform
   django database migrations.  These migrations do not need any interaction
   between services.

3. Initialize the Astakos quota system and bring the Astakos service up, since
   it will be needed during a second-phase of UUID and quota migrations, that
   also uses data extracted from step 1.


1. Bring all services down
==========================

All services must be brought down so that the database maintains a predictable
and consistent state as the migration is being executed.


2. Prepare astakos user migration to case insensitive emails
============================================================

It is possible that two or more users have been registered with emails that
differ only in the case of its letters.  There can only be one of those
accounts after the migration, so the rest must be deleted.

Note that even if the users are deleted in Astakos, there still are duplicate
entries in Cyclades and Pithos.  For each service we need to reduce those
multiple accounts into one, either merging them together, or deleting and
discarding data from all but one.

2.1 Find duplicate email entries in Astakos
-------------------------------------------
(script: ``find_astakos_users_with_conflicting_emails.py``)::

    astakos-host$ cat << EOF > find_astakos_users_with_conflicting_emails.py
    import os
    import sys
    
    os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'
    
    import astakos
    from astakos.im.models import AstakosUser as A
    
    def user_filter(user):
        return A.objects.filter(email__iexact=user.email).count() > 1
    
    all_users = list(A.objects.all())
    userlist = [(str(u.pk) + ': ' + str(u.email))
                for u in filter(user_filter, all_users)]
    sys.stderr.write("id: email\n")
    print "\n".join(userlist)
    
    EOF

    astakos-host$ python ./find_astakos_users_with_conflicting_emails.py


.. _remove_astakos_duplicate:

2.1 Remove duplicate users in Astakos by their id
-------------------------------------------------
(script: ``delete_astakos_users.py``)::

    astakos-host$ cat << EOF > delete_astakos_users.py
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
    print "id: email"
    print "--  -----"

    users = A.objects.filter(id__in=id_list)
    for user in users:
        print "%s: %s" % (user.id, user.email)

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

    MAKE SURE THAT YOU HAVE RESOLVED ALL CONFLICTS


3. Upgrade Synnefo and configure settings
=========================================

3.1 Install the new versions of packages
----------------------------------------

::

    astakos.host$ apt-get install \
                            snf-common \
                            snf-webproject \
                            snf-quotaholder-app \
                            snf-astakos-app \
                            kamaki \


    cyclades.host$ apt-get install \
                            snf-common \
                            snf-webproject
                            snf-pithos-backend \
                            snf-cyclades-app \
                            kamaki \

                           
    pithos.host$ apt-get install \
                            snf-common \
                            snf-webproject
                            snf-pithos-backend \
                            snf-pithos-app \
                            snf-pithos-webclient \
                            kamaki \

3.2 Sync and migrate Django DB
------------------------------

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

::

    # Service       Setting                       Value
    # quotaholder:  QUOTAHOLDER_TOKEN          = <random string>

    # astakos:      ASTAKOS_QUOTAHOLDER_TOKEN  = <the same random string>
    # astakos:      ASTAKOS_QUOTAHOLDER_URL    = https://quotaholder.host/quotaholder/v

    # cyclades:     CYCLADES_QUOTAHOLDER_TOKEN = <the same random string>
    # cyclades:     CYCLADES_QUOTAHOLDER_URL   = http://quotaholder.host/quotaholder/v
    # cyclades:     CYCLADES_USE_QUOTAHOLDER   = True


    # pithos:       PITHOS_QUOTAHOLDER_TOKEN   = <the same random string>
    # pithos:       PITHOS_QUOTAHOLDER_URL     = http://quotaholder.host/quotaholder/v
    # All services must match the quotaholder token and url configured for quotaholder.

3.4 Setup astakos
-----------------

- **Remove** this redirection from astakos front-end web server::

        RewriteRule ^/login(.*) /im/login/redirect$1 [PT,NE]

    (see `<http://docs.dev.grnet.gr/synnefo/latest/quick-install-admin-guide.html#apache2-setup>`_)

- Enable users to change their contact email with the setting::

      # astakos:        ASTAKOS_EMAILCHANGE_ENABLED = True

3.6 Setup Cyclades
------------------

- Make sure this setting is set::

    # cyclades: CYCLADES_ASTAKOS_SERVICE_TOKEN

  from the value in::

    cyclades.host$ snf-manage service-list

- VMAPI needs a **memcached** backend. To install::

        apt-get install memcached
        apt-get install python-memcache


  Set the IP address and port of the memcached deamon::

    VMAPI_CACHE_BACKEND = "memcached://127.0.0.1:11211"
    VMAPI_BASE_URL = "https://cyclades.okeanos.grnet.gr/"

  .. note::

    - These settings are needed in all Cyclades workers.

    - memcached must be reachable from all Cyclades workers.

    - For more information about configuring django to use memcached:
      https://docs.djangoproject.com/en/1.2/topics/cache

3.6 Setup Pithos
----------------

- Pithos forwards user catalog services to Astakos so that web clients may
  access them for uuid-displayname translations::

    # pithos:       PITHOS_USER_CATALOG_URL    = https://astakos.host/user_catalogs/
    # pithos:       PITHOS_USER_FEEDBACK_URL   = https://astakos.host/feedback/
    # pithos:       PITHOS_USER_LOGIN_URL      = https://astakos.host/login/
    # pithos:       #PITHOS_PROXY_USER_SERVICES = True # Set False if astakos & pithos are on the same host


4. Start astakos and quota services
===================================
E.g.::

    astakos.host$ service gunicorn restart


.. _astakos-load-resources:

5. Load resource definitions into Astakos
=========================================

Configure and load the available resources per service
and associated default limits into Astakos::

    astakos.host$ snf-manage astakos-load-service-resources

Example astakos settings (from `okeanos.io <https://okeanos.io/>`_)::

    # Set the cloud service properties
    ASTAKOS_SERVICES = {
        'cyclades': {
            #This can also be set from a management command
            'url': 'https://cyclades.host/ui/',
            'order': 0,
            'resources': [{
                'name':'disk',
                'group':'compute',
                'uplimit':300*1024*1024*1024,
                'unit':'bytes',
                'desc': 'Virtual machine disk size'
                },{
                'name':'cpu',
                'group':'compute',
                'uplimit':24,
                'desc': 'Number of virtual machine processors'
                },{
                'name':'ram',
                'group':'compute',
                'uplimit':40*1024*1024*1024,
                'unit':'bytes',
                'desc': 'Virtual machines'
                },{
                'name':'vm',
                'group':'compute',
                'uplimit':5,
                'desc': 'Number of virtual machines'
                },{
                'name':'network.private',
                'group':'network',
                'uplimit':5,
                'desc': 'Private networks'
                }
            ]
        },
        'pithos+': {
            'url': 'https://pithos.host/ui/',
            'order': 1,
            'resources':[{
                'name':'diskspace',
                'group':'storage',
                'uplimit':20 * 1024 * 1024 * 1024,
                'unit':'bytes',
                'desc': 'Pithos account diskspace'
                }]
        }
    }

.. note::

    Before v0.13, only `cyclades.vm`, `cyclades.network.private`,
    and `pithos+.diskspace` existed (not with this names, of course).
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

    cyclades.host$ snf-manage cyclades-astakos-migrate-0.13 --validate

Duplicate user found?

- either *merge* (merge will merge all resources to one user)::

    cyclades.host$ snf-manage cyclades-astakos-migrate-0.13 --merge-user=kpap@grnet.gr

- or *delete* ::

    cyclades.host$ snf-manage cyclades-astakos-migrate-0.13 --delete-user=KPap@grnet.gr
    # (only KPap will be deleted not kpap)

6.2 Migrate Cyclades users (email case/uuid)
--------------------------------------------

::

    cyclades.host$ snf-manage cyclades-astakos-migrate-0.13 --migrate-users

- if invalid usernames are found, verify that they do not exist in astakos::

    astakos.host$ snf-manage user-list

- if no user exists::

    cyclades.host$ snf-manage cyclades-astakos-migrate-0.13 --delete-user=<userid>

6.3 Migrate Pithos user names
-----------------------------

Check if alembic has not been initialized ::

    pithos.host$ pithos-migrate-0.13 current

- If alembic current is None (e.g. okeanos.io) ::

    pithos.host$ pithos-migrate-0.13 stamp 3dd56e750a3

Finally, migrate pithos account name to uuid::

    pithos.host$ pithos-migrate-0.13 upgrade head

7. Migrate old quota limits
===========================

7.1 Migrate Pithos quota limits to Astakos
------------------------------------------

Migrate from pithos native to astakos/quotaholder.
This requires a file to be transfered from Cyclades to Astakos::

    pithos.host$ snf-manage pithos-export-quota --location=pithos-quota.txt
    pithos.host$ rsync -avP pithos-quota.txt astakos.host:
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
    cyclades.host$ rsync -avP cyclades-quota.txt astakos.host:
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

    cyclades.host$ snf-manage pithos-reset-usage

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

