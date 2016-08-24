Upgrade to Synnefo v0.19
^^^^^^^^^^^^^^^^^^^^^^^^

Introduction
============

Starting with version 0.19, Synnefo now targets Debian Jessie. Upgrading to
Synnefo 0.19 also requires upgrading your base system from wheezy to jessie.
This guide assumes that during this upgrade each node is upgraded fully to
jessie.

.. warning::

   Synnefo 0.19 upgrades to newer Django and Django's database migration tool
   is used instead of ``South``. Because of this, the upgrade to v0.19 *must*
   be executed only from version 0.18.

Upgrade Steps
=============

The upgrade steps are split in two sections:

#. Upgrade all ganeti nodes to Debian Jessie.
#. Upgrade all service nodes to Debian Jessie.


Upgrade Ganeti nodes
====================

To achieve an upgrade with no VM downtime, you have to upgrade one ganeti node
at a time.

1. Evacuate ganeti node
-----------------------

2. Stop archipelago (?)
-----------------------

3. Upgrade node
--------------
* Change APT repos to jessie (apt.dev.grnet.gr and also ceph's if they exist)
* Upgrade all packages to jessie

.. code-block:: console

  # apt-get update
  # apt-get upgrade
  # apt-get dist-upgrade

4. Reboot node
--------------

After rebooting, the upgrade is complete and you can migrate VMs back to the
node, to proceed with the rest of the cluster.


# Is this feasible for production ??? Need to check witn NOC.
# Otherwise, shutdown all VMs, and perform the steps as described.


Upgrade Service nodes
=====================

1. Upgrade to Jessie
--------------------

* Change APT repos to jessie (including apt.dev.grnet.gr and also ceph's)
* Upgrade to jessie (install gevent/gunicorn from apt (1.1.1~grnet))

.. warning::

   Due to two bugs in gevent related to SSL found in debian's gevent 1.0.1, we
   have backported gevent 1.1.1 and greenlet 0.4.9 from stretch. Make sure you
   use these packages found on GRNet's Jessie repo.

.. code-block:: console

  # apt-get update
  # apt-get upgrade
  # apt-get dist-upgrade

2. Bring services down
----------------------

Shutdown gunicorn on all hosts:

.. code-block:: console

  # service gunicorn stop

Shutdown archipelago on pithos host:

.. code-block:: console

  # service archipelago stop


3. Run database migrations
--------------------------

Run database migrations in all nodes. This will upgrade from old south
migrations.

.. code-block:: console

  # snf-manage migrate


4. Adjust configuration files
-----------------------------

Change gunicorn configuration file
""""""""""""""""""""""""""""""""""

Newer gunicorn drops support for ``django`` mode. You must update the gunicorn
configuration file (by default ``/etc/gunicorn.d/synnefo``) on all nodes to
``wsgi`` mode by changing the ``mode`` setting to use the Synnefo's wsgi
entry point.

Example:

.. code-block:: console

  CONFIG = {
   'mode': 'wsgi',
   'environment': {
     'DJANGO_SETTINGS_MODULE': 'synnefo.settings',
   },
   'working_dir': '/etc/synnefo',
   'user': 'synnefo',
   'group': 'synnefo',
   'args': (
     '--bind=127.0.0.1:8080',
     '--worker-class=gevent',
     '--workers=8',
     '--log-level=info',
     '--timeout=43200',
     '--log-file=/var/log/synnefo/gunicorn.log',
     'synnefo.webproject.wsgi',
   ),
  }


New ALLOWED_HOSTS setting
"""""""""""""""""""""""""

Since Django 1.5, the ``ALLOWED_HOSTS`` setting is required in production.
Synnefo v0.19 adds a default value for this setting to ``['*']`` which allows
all hosts. You can change this setting on each node to restrict the hosts that
Django is allowed to serve.


Update cache settings
"""""""""""""""""""""

In cyclades, you now have to set each one of the three caches in a new format.
Defaults are:

.. code-block:: python

  PUBLIC_STATS_CACHE = {
      "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
      "LOCATION": "",
      "KEY_PREFIX": "publicstats",
      "TIMEOUT": 300,
  }

  VM_PASSWORD_CACHE = {
      "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
      "LOCATION": "",
      "KEY_PREFIX": "vmpassword",
      "TIMEOUT": None,
  }

  VMAPI_CACHE = {
      "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
      "LOCATION": "",
      "KEY_PREFIX": "vmapi",
  }

If you want to use memcache, you will need to set ``BACKEND`` to
``django.core.cache.backends.memcached.MemcachedCache`` and specify the
``LOCATION`` as well.

Please adjust the new settings to match your previous setup.


.. note::

  Do not forget to add '.conf' suffix on apache's conf files.

.. note::

  Notice that Synnefo now logs in a dedicated file
  ``/var/log/synnefo/synnefo.log``, separately from gunicorn's logs.

5. Reboot
---------

Reboot to finish the system upgrade. After reboot, services should
automatically start.

OR

5. Bring services back up
-------------------------

Start archipelago on pithos host:

.. code-block:: console

  # service archipelago start


Start gunicorn on all hosts:

.. code-block:: console

  # service gunicorn start
