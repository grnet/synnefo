Upgrade to Synnefo v0.16
^^^^^^^^^^^^^^^^^^^^^^^^

Introduction
============

Starting with version 0.16, we introduce Archipelago as the new storage backend
for the Pithos Service. Archipelago will act as a storage abstraction layer
between Pithos and NFS, RADOS or any other storage backend driver that
Archipelago supports. In order to use the Pithos Service you must install
Archipelago on the node that runs the Pithos and Cyclades workers.
Additionally, you must install Archipelago on the Ganeti nodes and upgrade
snf-image to version 0.16.2 since this is the first version that supports
Archipelago.

Until now the Pithos mapfile was a simple file containing a list of hashes that
make up the stored file in a Pithos container. After this consolidation the
Pithos mapfile had to be converted to an Archipelago mapfile. An Archipelago
mapfile is an updated version of the Pithos mapfile, intended to supersede it.

More info about the new mapfile you can find in Archipelago documentation.


Current state regarding ownerships and permissions
==================================================

In Synnefo v0.15, all Synnefo components run as ``www-data:www-data``. Also, in
case Pithos is using the NFS backend store, the files in the shared directory
are owned by ``www-data:www-data`` with ``0640`` permissions. Finally,
Archipelago, if used, runs as ``root:root``.

Synnefo v0.16 provides more flexibility regarding required users and
permissions. Synnefo introduces a dedicated system user and group:
``synnefo``. On the other hand, Archipelago v0.4 is able to run as an
arbitrary user/group (defaults to ``archipelago:archipelago``).

As already mentioned, in Synnefo v0.16, Archipelago is becoming the
storage backend for Pithos, so we must guarantee that Pithos will have
the right permissions to communicate with Archipelago. For this reason
we run Archipelago with the ``synnefo`` group.

Finally, in case NFS is used as a storage backend, we must also update
the permissions and ownerships of all directories and files on the
exported directory. Because this procedure may take a while in a production
setup with many TB of data, these upgrade notes provide a detailed procedure
in order to be able to perform the transition with minimum downtime.

At the end of the day Synnefo (Cyclades, Pithos, Astakos, etc) will run
as ``synnefo:synnefo`` while Archipelago will run as
``archipelago:synnefo``. The NFS (if any) will be owned by
``archipelago:synnefo`` with 2660 permissions.


Upgrade Steps
=============

The upgrade to v0.16 consists of the following steps:

0. Upgrade snf-image on all Ganeti nodes

1. Setup Archipelago on all nodes

2. Ensure intermediate state

3. Bring down services and backup databases

4. Upgrade packages, migrate the databases and configure settings

5. Inspect and adjust resource limits

6. Tweak Gunicorn settings on Pithos and Cyclades node

7. Bring up all services

8. Finalize permissions

9. Add unique names to disks of all Ganeti instances


.. warning::

    It is strongly suggested that you keep separate database backups
    for each service after the completion of each step.

0. Upgrade snf-image on all Ganeti nodes
========================================

On all Ganeti VM-capable nodes install the latest snf-image package (v0.16.3).

.. code-block:: console

  # apt-get install snf-image


1. Setup Archipelago on all nodes
==================================

At this point, we will perform some intemediate migration steps in order to
perform the upgrade procedure with minimum downtime. To achieve this, we will
pass through an intermediate state where:

* Pithos will run as ``www-data:synnefo``.
* Archipelago will run as ``archipelago:synnefo``.
* The NFS shared directory will be owned by ``www-data:synnefo`` with ``2660``
  permissions.

To ensure seamless transition we do the following:

* **Create system users and groups in advance**

  NFS expects the user and group ID of the owners of the exported directory
  to be common across all nodes. So we need to guarantee that ID of ``archipelago``
  user/group and ``synnefo`` group will be the same to all nodes.
  So we modify the ``archipelago`` user and group and create the ``synnefo``
  user (assuming that ids 200 and 300 are available everywhere), by running
  the following commands to all nodes that have archipelago installed:

  .. code-block:: console

    # addgroup --system --gid 200 synnefo
    # adduser --system --uid 200 --gid 200 --no-create-home \
        --gecos Synnefo synnefo

    # addgroup --system --gid 300 archipelago
    # adduser --system --uid 300 --gid 300 --no-create-home \
        --gecos Archipelago archipelago

  Normally the ``snf-common`` and ``archipelago`` packages are responsible
  for creating the required system users and groups.

* **Upgrade/Install Archipelago**

  Up until now Archipelago was optional. So, your setup, either has no
  Archipelago installation or has Archipelago v0.3.5 installed and
  configured in all VM-capable nodes. Depending on your case refer to:

   * `Archipelago installation guide <https://www.synnefo.org/docs/archipelago/latest/install-guide.html>`_
   * `Archipelago upgrade notes <https://www.synnefo.org/docs/archipelago/latest/upgrades/upgrade-0.4.html>`_

  Archipelago does not start automatically after installation. Do not start it
  manually until it is configured properly.

* **Adjust Pithos umask setting**

  On the Pithos node, edit the file
  ``/etc/synnefo/20-snf-pithos-app-settings.conf`` and uncomment or add the
  ``PITHOS_BACKEND_BLOCK_UMASK`` setting and set it to value ``0o007``.

  Then perform a gunicorn restart on both nodes:

  .. code-block:: console

      # service gunicorn restart

  This way, all files and directories created by Pithos will be writable by the
  group that Pithos is running (i.e. ``www-data``).

* **Change Pithos data group permissions**

  Ensure that every file and folder under Pithos data directory has correct
  permissions.

  .. code-block:: console

      # find /srv/pithos/data -type d -exec chmod g+rwxs '{}' \;
      # find /srv/pithos/data -type f -exec chmod g+rw '{}' \;

  This way, we prepare NFS to be fully accessible either via
  the user or the group.

* **Change gunicorn group**

  On the Pithos node, edit the file ``/etc/gunicorn.d/synnefo`` and set
  ``group`` to ``synnefo``. Then change the ownership of all
  configuration and log files:

  .. code-block:: console

     # chgrp -R synnefo /etc/synnefo
     # chgrp -R synnefo /var/log/synnefo
     # /etc/init.d/gunicorn restart

  This way, Pithos is able to access NFS via gunicorn user
  (``www-data``). We prepare Pithos to be able to access the ``synnefo``
  group.

* **Change Pithos data group owner**

  Make ``synnefo`` group the group owner of every file under the Pithos data
  directory.

  .. code-block:: console

      # chgrp synnefo /srv/pithos/data
      # find /srv/pithos/data -type d -exec chgrp synnefo '{}' \;
      # find /srv/pithos/data -type f -exec chgrp synnefo '{}' \;

  From now on, every file or directory created under the Pithos data directory
  will belong to the ``synnefo`` group because of the directory SET_GUID bit
  that we set on a previous step. Plus the ``synnefo`` group will have
  full read/write access because of the adjusted Pithos umask setting.

* **Make archipelago run as synnefo group**

  Change the Archipelago configuration on all nodes, to run as
  ``archipelago``:``synnefo``, since it no longer requires root
  priviledges. For each Archipelago node:

  * Stop Archipelago

    .. code-block:: console

      # archipelago stop

  * Change the ``USER`` and ``GROUP`` configuration option to ``archipelago``
    and ``synnefo`` respectively. The configuration file is located under
    ``/etc/archipelago/archipelago.conf``

  * Change the ownership of Archipelago log files:

    .. code-block:: console

      # chown -R archipelago:synnefo /var/log/archipelago

  * Start Archipelago

    .. code-block:: console

      # archipelago start


2. Ensure intermediate state
============================

Please verify that Pithos runs as ``www-data:synnefo`` and any file
created in the exported directory will be owned by ``www-data:synnefo``
with ``660`` permissions. Archipelago runs as ``archipelago:synnefo`` so it
can access NFS via the ``synnefo`` group. NFS (``blocks``, ``maps``,
``locks`` and all other subdirectories under ``/srv/pithos/data`` or
``/srv/archip``) will be owned by ``www-data:synnefo`` with 2770
permissions.


3. Bring web services down, backup databases
============================================

1. All web services must be brought down so that the database maintains a
   predictable and consistent state during the migration process::

    $ service gunicorn stop
    $ service snf-dispatcher stop
    $ service snf-ganeti-eventd stop

2. Backup databases for recovery to a pre-migration state.

3. Keep the database servers running during the migration process.


4. Upgrade Synnefo and configure settings
=========================================

4.1 Install the new versions of packages
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
                            snf-pithos-backend \
                            snf-network \
                            snf-image

.. note::

   Make sure ``snf-webproject`` has the same version with snf-common

.. note::

    Installing the packages will cause services to start. Make sure you bring
    them down again (at least ``gunicorn``, ``snf-dispatcher``)

.. note::

    If you are using qemu-kvm from wheezy-backports, note that qemu-kvm package
    2.1+dfsg-2~bpo70+2 has a bug that is triggered by snf-image. Check
    `snf-image installation <https://www.synnefo.org/docs/synnefo/latest/install-guide-debian.html#installation>`_ for
    a workaround.


4.2 Sync and migrate the database
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


4.3 Configure snf-vncauthproxy
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

    When installing snf-vncauthproxy on the same node as Cyclades and using the
    default settings for snf-vncauthproxy, the certificates should be issued to
    the FQDN of the Cyclades worker. Refer to the :ref:`admin guide
    <admin-guide-vnc>`, for more information on how to setup vncauthproxy on a
    different host / interface.

For more information on how to setup snf-vncauthproxy check the
snf-vncauthproxy `documentation <https://www.synnefo.org/docs/snf-vncauthproxy/latest/index.html#usage-with-synnefo>`_
and `upgrade notes <https://www.synnefo.org/docs/snf-vncauthproxy/latest/upgrade/upgrade-1.6.html>`_.

4.4 Re-register service and resource definitions
------------------------------------------------

The Cyclades service definition has been updated and needs to be registered
again. On the Astakos node, run::

    astakos-host$ snf-component-register cyclades

This will detect that the Cyclades component is already registered and ask
to re-register. Answer positively. You need to enter the base URL and the UI
URL for Cyclades, just like during the initial registration.

.. note::

   You can run ``snf-manage component-list -o name,base_url,ui_url`` to
   inspect the currently registered base and UI URLs.


5. Inspect and adjust resource limits
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


6. Tweak Gunicorn settings
==========================

First we make Gunicorn run as ``synnefo:synnefo``, by setting the
``user`` and ``group`` option in Gunicorn configuration
file (``/etc/gunicorn.d/synnefo``).

Also on the Pithos and Cyclades node you also have to set the following:

* ``--config=/etc/synnefo/gunicorn-hooks/gunicorn-archipelago.py``


.. warning::

    If you have already installed Synnefo v0.16rc1 or v0.16rc2 you
    should replace ``pithos.conf.py`` with ``gunicorn-archipelago.py`` located
    under ``/etc/synnefo/gunicorn-hooks`` directory. Afterwards you
    can freely delete  ``pithos.conf.py`` conf file.

After setting the user/group that Gunicorn will run as, we must also make
sure that configuration and log files are accessible:

.. code-block:: console

    # chgrp -R synnefo /etc/synnefo/
    # chown -R synnefo:synnefo /var/log/synnefo/

On the Cyclades node, the ``snf-dispatcher`` must run as
``synnefo``:``synnefo``. In ``/etc/default/snf-dispatcher`` verify that
``SNF_USER`` and ``SNF_DSPTCH_OPTS`` settings are:

.. code-block:: console

  SNF_USER="synnefo:synnefo"
  SNF_DSPTCH_OPTS=""

Finally, verify that snf-dispatcher can access its log file (e.g.
``/var/log/synnefo/synnefo.log``):

.. code-block:: console

   # chown synnefo:synnefo /var/log/synnefo/dispatcher.log


7. Bring all services up
========================

After the upgrade is finished, we bring up all services:

.. code-block:: console

    astakos.host  # service gunicorn start
    cyclades.host # service gunicorn start

    pithos.host   # service gunicorn start

    cyclades.host # service snf-dispatcher start

8. Finalize permissions
=======================

At this point, and while the services are running, we will finalize the
permissions of existing directories and files in the NFS directory to match
the user/group that Archipelago is running:

.. code-block:: console

  # chown -R archipelago:synnefo /srv/pithos/data


9. Add unique names to disks of all Ganeti instances
=====================================================

Synnefo 0.16 introduces the Volume service which can handle multiple disks
per Ganeti instance. Synnefo assigns a unique name to each Ganeti disk and
refers to it by that unique name. After upgrading to v0.16, Synnefo must
assign names to all existing disks. This can be easily performed with a helper
script that is shipped with version 0.16:

.. code-block:: console

 cyclades.host$ /usr/lib/synnefo/tools/add_unique_name_to_disks
