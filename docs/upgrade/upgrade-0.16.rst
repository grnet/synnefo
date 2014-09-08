Upgrade to Synnefo v0.16
^^^^^^^^^^^^^^^^^^^^^^^^

Introduction
============

Starting with version 0.16, we introduce Archipelago as the new storage backend
for the Pithos Service. Archipelago will act as a storage abstraction layer
between Pithos and NFS, RADOS or any other storage backend driver that
Archipelago supports. In order to use the Pithos Service you must install
Archipelago on the node that runs the Pithos and Cyclades workers.
Additionally, you must install snf-image version 0.16 on the Ganeti nodes since
this is the first version that supports Archipelago.

Until now the Pithos mapfile was a simple file containing a list of hashes that
make up the stored file in a Pithos container. After this consolidation the
Pithos mapfile had to be converted to an Archipelago mapfile. An Archipelago
mapfile is an updated version of the Pithos mapfile, intended to supersede it.

More info about the new mapfile you can find in Archipelago documentation.


Upgrade Steps
=============

The upgrade to v0.16 consists of the following steps:

0. Upgrade / Install Archipelago and snf-image.

1. Bring down services and backup databases.

2. Upgrade packages, migrate the databases and configure settings.

3. Inspect and adjust resource limits.

4. Tweak Archipelago and Gunicorn settings on Pithos node

5. Bring up all services.

6. Add unique names to disks of all Ganeti instances


.. warning::

    It is strongly suggested that you keep separate database backups
    for each service after the completion of each step.


0. Upgrade / Install Archipelago and snf-image
==============================================

If you have never used Archipelago before, make sure to install Archipelago 0.4
on all Ganeti VM-capable nodes.

If you're upgrading from Archipelago 0.3.5, make sure to upgrade Archipelago
on all Ganeti nodes before starting the upgrade process. For more
information, check the Archipelago
`upgrade notes <https://www.synnefo.org/docs/archipelago/latest/upgrades/archipelago_upgrade_v04.rst>`_.

Once you have Archipelago 0.4 up and running, you can install snf-image 0.16.

At this point, you should also install Archipelago 0.4 on the Pithos and
Cyclades workers.


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
                            snf-pithos-webclient \
                            libxseg0 \
                            python-xseg \
                            python-archipelago \
                            archipelago

    ganeti.node$ apt-get install \
                            python-objpool \
                            snf-common \
                            snf-cyclades-gtools \
                            snf-pithos-backend \
                            snf-network \
                            snf-image

.. note::

   Make sure `snf-webproject' has the same version with snf-common

.. note::

    Installing the packages will cause services to start. Make sure you bring
    them down again (at least ``gunicorn``, ``snf-dispatcher``)

.. note::

    If you are using qemu-kvm from wheezy-backports, note that qemu-kvm package
    2.1+dfsg-2~bpo70+2 has a bug that is triggered by snf-image. Check
    `snf-image installation <https://www.synnefo.org/docs/synnefo/latest/install-guide-debian.html#installation>`_ for
    a workaround.


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


2.3 Configure snf-vncauthproxy
------------------------------

Synnefo 0.16 replaces the Java VNC client with an HTML5 Websocket client and
the Cyclades UI will always request secure Websocket connections. You should,
therefore, provide snf-vncauthproxy with SSL certificates signed by a trusted
CA. You can either copy them to `/var/lib/vncauthproxy/{cert,key}.pem` or
inform vncauthproxy about the location of the certificates (via the
`DAEMON_OPTS` setting in `/etc/default/vncauthproxy`).

::

    DAEMON_OPTS="--pid-file=$PIDFILE --cert-file=<path_to_cert> --key-file=<path_to_key>"

Both files should be readable by the `vncauthproxy` user or group.

.. note::

    At the moment, the certificates should be issued to the FQDN of the
    Cyclades worker.

For more information on how to setup snf-vncauthproxy check the
snf-vncauthproxy `documentation <https://www.synnefo.org/docs/snf-vncauthproxy/latest/index.html#usage-with-synnefo>`_
and `upgrade notes <https://www.synnefo.org/docs/snf-vncauthproxy/latest/upgrade/upgrade-1.6.html>`_.


3. Inspect and adjust resource limits
=====================================

Synnefo 0.16 brings significant changes at the project mechanism. Projects
are now viewed as a source of finite resources, instead of a means to
accumulate quota. They are the single source of resources, and quota are now
managed at a project/member level.

System-provided quota are now handled through special purpose
user-specific *system projects*, identified with the same UUID as the user.
These have been created during the database migration process. They are
included in the project listing with::

  snf-manage project-list --system-projects

All projects must specify quota limits for all registered resources. Default
values have been set for all resources, listed with::

  astakos-host$ snf-manage resource-list

Column `system_default` (previously known as `default_quota`) provides the
skeleton for the quota limits of user-specific system projects. Column
`project_default` is new and acts as skeleton for `applied` (non-system)
projects (i.e., for resources not specified in a project application).
Project defaults have been initialized during migration based on the system
default values: they have been set to `inf` if `system_default` is also `inf`,
otherwise set to zero.

This default, affecting all future projects, can be modified with::

  astakos-host$ snf-manage resource-modify <name> --project-default <value>

Till now a project definition contained one quota limit per resource: the
maximum that a member can get from the project. A new limit is introduced:
the grand maximum a project can provide to its members. This new project
limit is initialized during migration as `max members * member limit` (if
`max members` is not set, the double of current active members is assumed).

Existing projects can now be modified directly through the command line. In
order to change a project's resource limits, run::

  astakos-host$ snf-manage project-modify <project_uuid> --limit <resource_name> <member_limit> <project_limit>

With the new mechanism, when a new resource is allocated (e.g., a VM or a
Pithos container is created), it is also associated with a project besides
its owner. The migration process has associated existing resources with
their owner's system project. Note that users who had made use of projects to
increase their quota may end up overlimit on some resources of their system
projects and will need to *reassign* some of their reserved resources to
another project in order to overcome this restriction.


4. Tweak Archipelago and Gunicorn settings on Pithos node
=========================================================

After installing Archipelago on the  Pithos node we need to adjust the
configuration files according to our deployment needs.

For Archipelago the configuration file is located on
``/etc/archipelago/archipelago.conf``, where we need to adjust carefully at
least six configuration options:

* ``BLKTAP_ENABLED``: Must be set to false for the Pithos node, if the node does
  not host VMs (a.k.a is not VM_CAPABLE)
* ``USER``: The user that Archipelago will run as must be the same as the
  Gunicorn user.
* ``GROUP``: The group that Archipelago will run as must be the same as the
  Gunicorn group.
* ``SEGMENT_SIZE``: Adjust shared memory segment size according to your machine's
  RAM. The default value is 2GB which in some situations might exceed your
  machine's physical RAM.
* ``archip_dir`` in ``blockerm`` section must be set to the directory that
  Pithos mapfiles reside until now (e.g., ``/srv/pithos/data/maps``).
  For RADOS installations the ``pool`` setting must be set to the RADOS pool
  that Pithos mapfiles reside.
* ``archip_dir`` in ``blockerb`` section must be set to the directory that
  Pithos data blocks reside until now (e.g., ``/srv/pithos/data/blocks``).
  For RADOS installations the ``pool`` setting must be set to the RADOS pool
  that Pithos data blocks reside.

For Gunicorn the configuration file is located on ``/etc/gunicorn.d/synnefo``
where we need to change:

* ``--worker-class=gevent`` to ``--worker-class=pithos.workers.gevent_archipelago.GeventArchipelagoWorker``

and set:

* ``--config=/etc/synnefo/pithos.conf.py``


5. Bring all services up
========================

After the upgrade is finished, we bring up all services:

.. code-block:: console

    astakos.host  # service gunicorn start
    cyclades.host # service gunicorn start

    pithos.host   # service archipelago start
    pithos.host   # service gunicorn start

    cyclades.host # service snf-dispatcher start


6. Add unique names to disks of all Ganeti instances
=====================================================

Synnefo 0.16 introduces the Volume service which can handle multiple disks
per Ganeti instance. Synnefo assigns a unique name to each Ganeti disk and
refers to it by that unique name. After upgrading to v0.16, Synnefo must
assign names to all existing disks. This can be easily performed with a helper
script that is shipped with version 0.16:

.. code-block:: console

 cyclades.host$ /usr/lib/synnefo/tools/add_unique_name_to_disks
