Upgrade to Synnefo v0.15
^^^^^^^^^^^^^^^^^^^^^^^^


Prerequisites
==============

Before upgrading to v0.15 there are three steps that must be performed, relative
to the Cyclades networking service.

Add unique names to all NICs of all Ganeti instances
----------------------------------------------------

Since Ganeti 2.8, it is supported to give a name to a NIC of a Ganeti instance
and then refer to the NIC by that name (and not only by its index). Synnefo
v0.15 assigns a unique name to each NIC and refers to it by that unique name.
Before upgrading to v0.15, Synnefo must assign names to all existing NICs. This
can be easily performed with a helper script that is already shipped with
Synnefo v0.14.10:

.. code-block:: console

 cyclades.host$ /usr/lib/synnefo/tools/add_unique_name_to_nics

.. note:: If you are not upgrading from v0.14.10, you can find the migration
 script :ref:`here <add_names>`.

Extend public networks to all Ganeti backends
---------------------------------------------

Before v0.15, each public network of Cyclades existed in one of the Ganeti
backends. In order to support dynamic addition and removal of public IPv4
addresses across VMs, each public network must exist in all Ganeti backends.

If you are using more than one Ganeti backends, before upgrading to v0.15 you
must ensure that the network configuration of all Ganeti backends is identical
and appropriate to support all public networks of Cyclades.

Update Ganeti allocation policy
-------------------------------

Minimum number of NICs
``````````````````````
Before v0.15, all Cyclades VMs were forced to be connected to the public
network. Synnefo v0.15 supports more flexible configurations and dynamic
addition/removal of public IPv4 addresses, which can result in a VMs with no
NICs at all. However, Ganeti's default allocation policy will not allow
instances without NICs. You will have to override Ganeti's default allocation
policy to set the minimum number of NICs to zero. To do this, first get the
current allocation policy:

.. code-block:: console

 $ gnt-cluster show-ispecs-cmd
 gnt-cluster init --ipolicy-std-specs cpu-count=1,disk-count=1,disk-size=1024,memory-size=128,nic-count=1,spindle-use=1
   --ipolicy-bounds-specs min:cpu-count=1,disk-count=1,disk-size=1024,memory-size=128,nic-count=1,spindle-use=1/max:cpu-count=8,disk-count=16,disk-size=1048576,memory-size=32768,nic-count=8,spindle-use=12
   ganeti1.example.synnefo.org

And replace `min:nic-count=1` with `min:nic-count=0`. Also, set
`max:nic-count=32` to avoid reaching the default limit of 8.


.. code-block:: console

 gnt-cluster modify --ipolicy-bounds-specs min:cpu-count=1,disk-count=1,disk-size=1024,memory-size=128,nic-count=0,spindle-use=1/max:cpu-count=8,disk-count=16,disk-size=1048576,memory-size=32768,nic-count=32,spindle-use=12

Enabled and allowed disk templates
``````````````````````````````````
In v0.15, the ``ARCHIPELAGO_BACKENDS`` setting, that was used to separate
backends that were using Archipelago from the ones that were using all other
disk templates, has been removed. Instead, allocation of instances to Ganeti
backends is based on which disk templates are enabled and allowed in each
Ganeti backend (see section in :ref:`admin guide <alloc_disk_templates>`). You
can see the enabled/allowed disk templates by inspecting the corresponding
fields in the `gnt-cluster info` output. For example, to have a backend holding
only instances with archipelago disk templates, you can set the
`--ipolicy-disk-templates` to include only the `ext` disk template.

.. code-block:: console

 gnt-cluster modify --ipolicy-disk-templates=ext


Upgrade Steps
=============

The upgrade to v0.15 consists in the following steps:

1. Bring down services and backup databases.

2. Upgrade packages, migrate the databases and configure settings.

3. Create floating IP pools

4. Re-register services and resources.

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
                            snf-pithos-backend \
                            snf-network

.. note::

   Make sure 'snf-webproject' has the same version as 'snf-common'.

.. note::

   Installing the packages will cause services to start. Make sure you bring
   them down again (at least ``gunicorn``, ``snf-dispatcher``).

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

2.3 Configure Astakos authentication URL
----------------------------------------

The ``ASTAKOS_BASE_URL`` setting has been replaced (both in Cyclades and Pithos
services) with the ``ASTAKOS_AUTH_URL`` setting.

For Cyclades service we have to change the ``20-snf-cyclades-app-api.conf``
file, remove the ``ASTAKOS_BASE_URL`` setting and replace it with
``ASTAKOS_AUTH_URL``. Typically it is sufficient to add ``/identity/v2.0`` at
the end of base URL to get the auth URL. For example, if base URL had the value
of 'https://accounts.example.synnefo.org/' then the ``ASTAKOS_AUTH_URL``
setting will have the value of
'https://accounts.example.synnefo.org/identity/v2.0'.

The same change has to be made for the Pithos service in
``/etc/synnefo/20-snf-pithos-app-settings.conf``.

2.4 Register Pithos view as an OAuth 2.0 client in Astakos
----------------------------------------------------------

Starting from Synnefo version 0.15, the Pithos view, in order to get access to
the data of a protected Pithos resource, has to be granted authorization for
the specific resource by Astakos.

During the authorization grant procedure, it has to authenticate itself with
Astakos, since the latter has to prevent serving requests by
unknown/unauthorized clients.

Each oauth 2.0 client is identified by a client identifier (client_id).
Moreover, the confidential clients are authenticated via a password
(client_secret).
Then, each client has to declare at least a redirect URI so that astakos will
be able to validate the redirect URI provided during the authorization code
request.
If a client is trusted (like a pithos view) astakos grants access on behalf
of the resource owner, otherwise the resource owner has to be asked.

To register the pithos view as an OAuth 2.0 client in astakos, use the
following command::

    astakos-host$ snf-manage oauth2-client-add pithos-view --secret=<secret> --is-trusted --url <redirect_uri>

The redirect_uri should be the ``PITHOS_BASE_URL`` plus the ``/ui/view``
suffix, for example::

    https://node2.example.com/pithos/ui/view

You can see the registered clients by running::

    astakos-host$ snf-manage oauth2-client-list -o id,identifier,redirect_urls,is_trusted

Finally, you will have to add the registered `identifier` (e.g. `pithos-view`)
and `client_secret` to the ``PITHOS_OAUTH2_CLIENT_CREDENTIALS`` setting in
``/etc/synnefo/20-snf-pithos-app-settings.conf``.


2.5 Upgrade vncauthproxy and configure snf-cyclades-app
-------------------------------------------------------

Synnefo v0.15 adds support for snf-vncauthproxy >= 1.5 and drops support for
older versions. You will have to upgrade snf-vncauthproxy to v1.5 and
configure the authentication (users) file (``/var/lib/vncauthproxy/users``).

In case you are upgrading from an older snf-vncauthproxy version or if it's the
first time you're installing snf-vncauthproxy, you will need to add a
vncauthproxy user (see below for more information on user management) and
restart the vncauthproxy daemon.

To manage the authentication file, you can use the ``vncauthproxy-passwd`` tool,
to easily add, update and delete users.

To add a user:

.. code-block:: console

    # vncauthproxy-passwd /var/lib/vncauthproxy/users synnefo

You will be prompted for a password.

You should also configure the new ``CYCLADES_VNCAUTHPROXY_OPTS`` setting in
``snf-cyclades-app``, to provide the user and password configured for
``synnefo`` in the vncauthproxy authentication file and enable SSL support if
snf-vncauthproxy is configured to run with SSL enabled for the control socket.

.. warning:: The vncauthproxy daemon requires a restart for the changes in the
 authentication file to take effect.

.. warning:: If you fail to provide snf-vncauthproxy with a valid
 authentication file, or in case the configuration of vncauthproxy and the
 vncauthproxy snf-cyclades-app settings don't match (ie not having SSL enabled
 on both), VNC console access will not be functional.

Finally, snf-vncauthproxy-1.5 adds a dedicated user and group to be used by the
vncauthproxy daemon. The Debian default file has changed accordingly (``CHUID``
option in ``/etc/default/vncauthproxy``). The Debian default file now also
includes a ``DAEMON_OPTS`` variable which is used to pass any necessary/extra
options to the vncauthproxy daemon. In case you're ugprading from an older
version of vncauthproxy, you should make sure to 'merge' the new default file
with the older one.

Check the `documentation
<http://www.synnefo.org/docs/snf-vncauthproxy/latest/index.html>`_ of
snf-vncauthproxy for more information on upgrading to version 1.5.

2.6 Stats configuration
-----------------------

snf-cyclades-gtools comes with a collectd plugin to collect CPU and network
stats for Ganeti VMs and an example collectd configuration. snf-stats-app is a
Django (snf-webproject) app that serves the VM stats graphs by reading the VM
stats (from RRD files).

To enable/deploy the VM stats collecting and snf-stats-app, see the relevant
documentation in the :ref:`admin guide <admin-guide-stats>`.

If you were using collectd to collect VM stats on Debian Squeeze and you are
upgrading to Wheezy, you will need to upgrade your RRD files. Follow the
instructions on the collectd v4-to-v5 migration `guide
<https://collectd.org/wiki/index.php/V4_to_v5_migration_guide>`_.
You will probably just need to run the `migration script
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
value/string and make sure that it's the same as the ``STATS_SECRET_KEY``
setting (used to decrypt the instance hostname) in
``20-snf-stats-settings.conf`` on your Stats host.

2.7 Shibboleth configuration updates
------------------------------------

.. note::

  Skip this step unless you have ``shibboleth`` enabled in Astakos
  ``IM_MODULES`` setting.

As of v0.15 Astakos uses the ``REMOTE_USER`` header provided by Apache's
``mod_shib2`` service in order to resolve the unique identifier which is used
to associate a shibboleth account to a local Astakos user. Prior to this
version, Astakos adhered to the presence of the ``MOD_SHIB_EPPN`` header which
although safe enough on most of the ``SP`` deployment scenarios, it may cause
issues in certain cases, such as global wide IdP support or inability of
supported IdPs to release the ``eduPersonPrincipalName`` attribute. The
``REMOTE_USER`` header can be set by administrators to match any of the
available shibboleth attributes.

If ``EPPN`` matches the service provider needs and you want to continue using
it as the unique identifier, you need to ensure that the ``REMOTE_USER``
attribute is set to ``eppn`` in the ``mod_shib2`` config file located at
``/etc/shibboleth/shibboleth2.xml`` 

.. code-block:: xml

    <!-- The ApplicationDefaults element is where most of Shibboleth's SAML bits are defined. -->
    <ApplicationDefaults entityID="https://sp.example.org/shibboleth" REMOTE_USER="eppn">

Otherwise, if ``EPPN`` doesn't suit the requirements for your ``SP``
deployment, change the ``REMOTE_USER`` attribute as required e.g.:

.. code-block:: xml

    <!-- The ApplicationDefaults element is where most of Shibboleth's SAML bits are defined. -->
    <ApplicationDefaults entityID="https://sp.example.org/shibboleth" REMOTE_USER="persistent-nameid persistent-id targeted-id">

and restart the ``shibd`` service:

.. code-block:: console

  $ service shibd restart

**Note** that every time you alter the ``REMOTE_USER`` attribute, all existing
shibboleth enabled Astakos users will be invalidated and no longer be able to
login to their existing account using shibboleth. Specifically, for the case of
switching from *eppn* to another attribute, Astakos is able to prevent
invalidation and automatically migrate existing *eppn* accounts. In order to do
that, set the ``ASTAKOS_SHIBBOLETH_MIGRATE_EPPN`` setting to ``True`` in
``20-snf-astakos-app-settings.conf`` configuration file. Now every time an
existing *eppn* user logs in using shibboleth, Astakos will update the
associated *eppn* identifier to the contents of the ``REMOTE_USER`` header.

.. warning::
  
  IdPs should keep releasing the ``EPPN`` attribute in order for the migration
  to work.


3. Create floating IP pools
===========================

Synnefo v0.15 introduces floating IPs, which are public IPv4 addresses that can
be dynamically added/removed to/from VMs and are quotable via the
``cyclades.floating_ip`` resource. Connecting a VM to a public network is only
allowed if the user has first allocated a floating IP from this network.

Floating IPs are created from networks that are marked as Floating IP pools.
Creation of floating IP pools is done with the `snf-manage network-create`
command using the `--floating-ip-pool` option.

Existing networks can be converted to floating IPs using `network-modify`
command:

.. code-block:: console

  snf-manage network-modify --floating-ip-pool=True <network_ID>

Already allocated public IPv4 addresses are not automatically converted to
floating IPs. Existing VMs can keep their IPv4 addresses which will be
automatically released when these VMs get destroyed. If the admin wants to
convert existing public IPs to floating IPs, he/she can do so by running the
following provided tool:

.. code-block:: console

 cyclades.host$ /usr/lib/synnefo/tools/update_to_floating_ips

or just for one network:

.. code-block:: console

 cyclades.host$ /usr/lib/synnefo/tools/update_to_floating_ips --network-id=<network_ID>


4. Register services and resources
==================================

4.1 Re-register service and resource definitions
------------------------------------------------

You will need to register again all Synnefo components, updating the
service and resource definitions. On the Astakos node, run::

    astakos-host$ snf-component-register

This will detect that the Synnefo components are already registered and ask
to re-register. Answer positively. You need to enter the base URL and the UI
URL for each component, just like during the initial registration.

.. note::

   You can run ``snf-manage component-list -o name,ui_url`` to inspect the
   current registered UI URL. In the default installation, the base URL can
   be found by stripping ``/ui`` from the UI URL.

The meaning of resources ``cyclades.cpu`` and ``cyclades.ram`` has changed in
v0.15: they now denote the number of CPUs/RAM of *active* VMs (VMs that are not
shutdown) rather than all VMs as happened until now. To represent total CPUs
and total RAM, as previously, two new resources ``cyclades.total_cpu`` and
``cyclades.total_ram`` are introduced. We now also control the usage of
floating IPs through the resource ``cyclades.floating_ip``.

4.2 Tweek resource settings
---------------------------

The new resources (``cyclades.total_cpu``, ``cyclades.total_ram``, and
``cyclades.floating_ip``) are registered with infinite default base quota
(meaning that they are not restricted at all). You will probably need to
restrict them, especially ``cyclades.floating_ip``. In order to change the
default limit of a resource for all *future* users, for instance restricting
floating IPs to 2, run::

    astakos-host$ snf-manage resource-modify cyclades.floating_ip --default-quota 2

Note that this command does not affect *existing* users any more. They can
still have infinite floating IPs. You can update base quota of existing
users in bulk, possibly excluding some users, with::

    astakos-host$ snf-manage user-modify --all --base-quota cyclades.floating_ip 2 --exclude userid1,userid2

.. note::

   You can inspect base quota with ``snf-manage quota-list``, before applying
   any changes, for example::

     # Get users with cyclades.vm base quota that differ from the default value
     astakos-host$ snf-manage quota-list --with-custom=True --filter-by "resource=cyclades.vm"

     # Get users with cyclades.vm base quota greater than 3
     astakos-host$ snf-manage quota-list --filter-by "resource=cyclades.vm,base_quota>3"

Furthermore in v0.15, it is possible to control whether a resource is visible
to the users via the API or the Web UI. The default value for these options is
denoted inside the default resource definitions. Note that the system always
checks and enforces resource quota, regardless of their visibility. By default,
the new resources ``cyclades.total_cpu``, ``cyclades.total_ram`` and
``astakos.pending_app`` are not visible neither via the API nor via the Web UI.
You can change this behavior with::

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
