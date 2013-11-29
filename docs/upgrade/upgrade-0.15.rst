Upgrade to Synnefo v0.15
^^^^^^^^^^^^^^^^^^^^^^^^

Prerequisites
==============

Before upgrading to v0.15 there are two steps that must be performed, relative
with Cyclades networking service.

Add unique name to the NICs of all Ganeti instances
---------------------------------------------------

Since Ganeti 2.8, it is supported to give a name to NICs of Ganeti instances
and refer to them with their name, and not only by their index. Synnefo v0.15
assigns a unique name to each NIC and refers to them by their unique name.
Before upgrading to v0.15, Synnefo must assign names to all existing NICs.
This can easily be performed with a helper script that is shipped with Synnefo
v0.14.10:

.. code-block:: console

 cyclades.host$ /usr/lib/synnefo/tools/add_unique_name_to_nics

.. note:: If you are not upgrading from v0.14.10, you can find the migration
 script here XXX.


Extend public networks to all Ganeti backends
---------------------------------------------

Before v0.15, each public network of Cyclades existed in one of the Ganeti
backends. In order to support dynamic addition and removal of public IPv4
address across VMs, each public network must exist in all Ganeti backends.

If you are using more than one Ganeti backends, before upgrading to v0.15 you
must ensure that the network configuration to all Ganeti backends is identical
and appropriate to support all public networks of Cyclades.


Upgrade Steps
=============

The upgrade to v0.15 consists in the following steps:

1. Bring down services and backup databases.

2. Upgrade packages, migrate the databases and configure settings.

3. Create floating IP pools

4. Register services and resources.

5. Bring up all services.

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


2.5 Stats configuration
-----------------------

snf-cyclades-gtools comes with a collectd plugin to collect CPU and network
stats for Ganeti VMs and an example collectd configuration. snf-stats-app is a
Django (snf-webproject) app that serves the VM stats graphsmm by reading the VM
stats (from RRD files) and serves graphs.

To enable / deploy VM stats collecting and snf-stats-app see the relevant
documentation in the :ref:`admin guide <admin-guide-stats>`.

If you were using collectd to collect VM stats on Debian squeeze and you are
upgrading to Wheezy, you will need to upgrade your RRD files. Follow the
instructions on the collectd v4-to-v5 migration `guide
<https://collectd.org/wiki/index.php/V4_to_v5_migration_guide>`_.
You will proabably just need to run the `migration script
<https://collectd.org/wiki/index.php/V4_to_v5_migration_guide#Migration_script>`_
provided.

If you were using a previous version of snf-stats-app, you should also make
sure to set the ``STATS_BASE_URL`` setting in ``20-snf-stats-app-settings.conf``
to match your deployment and change the graph URL settings in
``20-snf-cyclades-app-api.conf`` accordingly.

v0.15 has also introduced the ``CYCLADES_STATS_SECRET_KEY`` and
``STATS_SECRET_KEY`` settings. ``CYCLADES_STATS_SECRET_KEY`` in
``20-snf-cyclades-app-api.conf`` is used by Cyclades to encrypt the instance id
/ hostname  in the URLs serving the VM stats. You should set it to a random
value / string and make sure that it's the same as the ``STATS_SECRET_KEY``
setting (used to decrypt the instance hostname) in
``20-snf-stats-settings.conf`` on your Stats host.

3. Create floating IP pools
===========================

Synnefo v0.15 introduces floating IPs, which are public IPv4 addresses that can
dynamically be added/removed to/from VMs and are quotable via the
'cyclades.floating_ip' resource. Connecting a VM to a public network is only
allowed if the user has firstly created a floating IP from this network.

Floating IPs are created from networks that are marked as Floating IP pools.
Creation of floating IP pools is done with the `snf-manage network-create`
command using the `--floating-ip-pool` option.

Existing networks can be converted to floating IPs using `network-modify`
command:

.. code-block:: console

  snf-manage network-modify --floating-ip-pool=True <network_ID>

Already allocated public IPv4 addresses are not automatically converted to
floating IPs. Existing VMs can keep their IPv4 addresses which will be
automatically be released when these VMs will be destroyed. In order to
convert existing public IPs to floating IPs run the following command:

.. code-block:: console

 cyclades.host$ /usr/lib/synnefo/tools/update_to_floating_ips

or for just one network:

.. code-block:: console

 cyclades.host$ /usr/lib/synnefo/tools/update_to_floating_ips --network-id=<network_ID>

4. Register services and resources
==================================

4.1 Re-register service and resource definitions
------------------------------------------------

You will need to register again all Synnefo components, updating the
service and resource definitions. On the astakos node, run::

    astakos-host$ snf-component-register

This will detect that the Synnefo components are already registered and ask
to re-register. Answer positively. You need to enter the base URL and the UI
URL for each component, just like during the initial registration.

.. note::

   You can run ``snf-manage component-list -o name,ui_url`` to inspect the
   current registered UI URL. In the default installation, the base URL can
   be found by stripping ``/ui`` from the UI URL.

The meaning of resources ``cyclades.cpu`` and ``cyclades.ram`` has changed:
they now denote the number of CPUs and, respectively, RAM of *active* VMs
rather than all VMs. To represent total CPUs and total RAM, as previously,
new resources ``cyclades.total_cpu`` and ``cyclades.total_ram`` are
introduced. We now also control the usage of floating IPs through resource
``cyclades.floating_ip``.

4.2 Tweek resource settings
---------------------------

New resources (``cyclades.total_cpu``, ``cyclades.total_ram``, and
``cyclades.floating_ip``) are registered with infinite default base quota.
You will probably need to restrict them, especially
``cyclades.floating_ip``. In order to change the default for all *future*
users, for instance restricting floating IPs to 2, run::

    astakos-host$ snf-manage resource-modify cyclades.floating_ip --default-quota 2

Note that this command does not affect *existing* users any more. They can
still have infinite floating IPs. You can update base quota of existing
users in bulk, possibly excluding some users, with::

    astakos-host$ snf-manage user-modify --all --base-quota cyclades.floating_ip 2 --exclude uuid1,uuid2

.. note::

   You can inspect base quota with ``snf-manage quota-list`` before applying
   any changes, for example::

     # Get users with cyclades.vm base quota that differ from the default value
     astakos-host$ snf-manage quota-list --with-custom=True --filter-by "resource=cyclades.vm"

     # Get users with cyclades.vm base quota greater than 3
     astakos-host$ snf-manage quota-list --filter-by "resource=cyclades.vm,base_quota>3"

It is now possible to control whether a resource is visible for the users
through the API or the UI. Note that the system always checks resource
quota, regardless of their visibility. By default, ``cyclades.total_cpu``,
``cyclades.total_ram`` and ``astakos.pending_app`` are not visible. You can
change this behavior with::

    astakos-host$ snf-manage resource-modify <resource> --api-visible=True (or --ui-visible=True)

4.3 Update the Quotaholder
--------------------------

To update quota for all new or modified Cyclades resources, bring up Astakos::

    astakos-host$ service gunicorn start

and run on the Cyclades node::

   cyclades-host$ snf-manage reconcile-resources-cyclades --fix --force


5. Bring all services up
========================

After the upgrade is finished, we bring up all services:

.. code-block:: console

    astakos.host  # service gunicorn start
    cyclades.host # service gunicorn start
    pithos.host   # service gunicorn start

    cyclades.host # service snf-dispatcher start
