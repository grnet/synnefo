Upgrade to Synnefo v0.17
^^^^^^^^^^^^^^^^^^^^^^^^

Upgrade Steps
=============

The upgrade to v0.17 consists of the following steps:

0. Upgrade Archipelago on all nodes to the latest version (0.4.4).

   .. note::

     For Pithos nodes see below.

   .. code-block:: console

     host# archipelago stop --pause
     host# apt-get upgrade
     host# archipelago start


    On Pithos node, the gunicorn must also be stopped first:

   .. code-block:: console

     host# service gunicorn stop
     host# archipelago stop --pause
     host# apt-get upgrade
     host# archipelago start
     host# service gunicorn start

1. Upgrade Ganeti on all nodes to the latest version ()

   .. code-block:: console

     host# apt-get upgrade
     host# service gunicorn restart

2. Upgrade Synnefo on all nodes to the latest version (0.17)

3. Install the Ganeti and Synnefo. For the following steps, the Cyclades API
   must be down.

   .. code-block:: console

     cyclades.host# service gunicorn stop

4. Run the migrations for the Cyclades DB:

   .. code-block:: console

     cyclades.host$ snf-manage migrate db

5. Update the names of Archipelago volumes:

   .. code-block:: console

     cyclades.host$ /usr/lib/synnefo/tools/rename_unique_name_of_disks


   .. warning:: This script must not be re-run after cyclades API is started.

6. Create helper VMs in all Ganeti clusters.

   Helper VMs are required for the deletion of detachable volumes. These helper
   VMs must be attributed to a user, and thus an admin account must be created.
   The account can be the same as the one used for the upload of the images.

   Before creating the helper VMs, you need to bring the Cyclades API back up,
   but firewall it from the outside world.

   In order to facilitate the creation of helper VMs, we have created an
   snf-manage command for this purpose:

   .. code-block:: console

     cyclades.host$ snf-manage helper-servers-sync --flavor <flavor_id> \
                      --image <image_id> --user <admin_user_id> \
                      --password *****


   The above script will create a helper server in all online Ganeti clusters
   and will immediately shut it down so that it reserves no resources.

   .. note::

     You must choose a flavor which has an Archipelago disk template.

7. Once the syncing of the helper servers has finished, you can remove the
   firewall from the Cyclades API.

8. On the node where pithos UI (`snf-pithos-webclient`) package is installed,
   remove existing pithos UI package and install the `snf-ui-app` package.
   The `snf-pithos-webclient` package is deprecated and should no longer be
   installed in any of your service nodes.

   .. code-block:: console

     (pithos-ui-node)$ apt-get remove snf-pithos-webclient --purge
     (pithos-ui-node)$ apt-get install snf-ui-app

  Edit `/etc/synnefo/20-snf-ui-cloudbar.conf` and
  `/etc/synnefo/20-snf-ui-settings.conf` to match your deployment
  configuration.

  Notice that the new UI application no longer redirects service root paths
  to the pithos UI endpoint. If you want to preserve this behaviour consider
  adding a rewrite rule such as the following in your apache vhost
  configuration.

  .. code-block:: console

    RewriteRule ^/$ /ui [R=302]

9. As of 0.17 admins can set their own implementation of backend allocator
   mechanism. Due to this change the default BACKEND_ALLOCATOR_MODULE setting
   is now changed to "synnefo.logic.allocators.default_allocator.DefaultAllocator".
   Notice that previous default value for this setting is no longer supported.

10. As of 0.17 VM passwords are stored to a volatile memory cache. This allows 
    cyclades UI to inform users who accidentally forgot the password provided 
    during vm creation process of the password once they open the machine 
    connection info modal. The password is removed from cache once the user 
    explicitly accepts that the password is written down or once a specific 
    period is reached. To enable this feature add the following setting in 
    `20-snf-cyclades-app-api.conf` (you may use the same memcached 
    server as the one in `VMAPI_CACHE_BACKEND`):

    .. code-block:: python
    
        CACHE_BACKEND = '<memcached-server-uri>'

    or you may use the format below to change the default timeout period:

    .. code-block:: python
    
        CACHE_BACKEND = '<memcached-server-uri>/?timeout=3600'
