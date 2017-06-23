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
   be executed only from version 0.18.1.

.. note::

   API endpoint listing has been modified in Synnefo v0.19 to be more Openstack
   compatible. This introduces a breaking API change and the users of the cloud
   service must upgrade their ``Kamaki`` client to ``Kamaki >= 0.15``. For more
   information regarding the changes, refer to the Changelog.


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

You must first evacuate the node in order to upgrade Archipelago.


2. Stop archipelago
-------------------

.. code-block:: console

  # service archipelago stop


3. Upgrade node
---------------

* Change all APT repos to jessie, including apt.dev.grnet.gr and also ceph's if
  they exist.
* Upgrade all packages to jessie

.. code-block:: console

  # apt-get update
  # apt-get dist-upgrade


4. Reboot node
--------------

After rebooting, the upgrade is complete and you can migrate VMs back to the
node, to proceed with the rest of the cluster.


Upgrade Service nodes
=====================


1. Change repos to Jessie
-------------------------

* Change all APT repos to jessie, including apt.dev.grnet.gr and also ceph's if
  they exist.

.. code-block:: console

  # apt-get update


2. Bring services down
----------------------

Shutdown gunicorn on all hosts:

.. code-block:: console

  # service gunicorn stop

Shutdown archipelago on pithos and cyclades hosts:

.. code-block:: console

  # service archipelago stop

Shutdown snf-dispatcher on cyclades host:

.. code-block:: console

  # service snf-dispatcher stop

Shutdown snf-ganeti-eventd on ganeti master candidates:

.. code-block:: console

  # service snf-ganeti-eventd stop


3. Upgrade to jessie
--------------------

* Upgrade to jessie.

.. code-block:: console

  # apt-get dist-upgrade

.. warning::

   Due to two bugs in gevent related to SSL found in debian's gevent 1.0.1, you
   should use the gevent 1.1.1-2 and greenlet 0.4.10-1 from jessie-backports.

.. warning::

   After package installation some services automatically start. You must shut
   them down again. Alternatively, you can use the
   `policy-rc.d <https://people.debian.org/~hmh/invokerc.d-policyrc.d-specification.txt>`_
   funcionality to disallow this functionality.

Shutdown gunicorn on all hosts:

.. code-block:: console

  # service gunicorn stop

Shutdown snf-dispatcher on cyclades host:

.. code-block:: console

  # service snf-dispatcher stop

Shutdown snf-ganeti-eventd on ganeti nodes:

.. code-block:: console

  # service snf-ganeti-eventd stop


3. Run database migrations
--------------------------

Run database migrations in all service nodes (i.e. if a service consists of
multiple nodes/workers, you must run the migrations **only in one** of them).
This will upgrade from old south migrations:

.. code-block:: console

  # snf-manage migrate


Fix IP history inconsistencies
""""""""""""""""""""""""""""""

Prior to 0.19, changing the owner of a VM with attached IPs would break the
recorded IP history. In particular, the association of the past owner with
the attached IP would be lost.

If you have made such changes and you have kept a log of them, you can
recover the IP history with the following tool::

  cyclades.host$ /usr/lib/synnefo/tools/fix_ip_history <changelog_file>

The command argument is the filename of your VM owner changelog. Each VM
owner change should be described in a separate line, in the following
format (date should be in UTC)::

  <vmid>|<from_uuid>|<to_uuid>|<%Y-%m-%d %H:%M:%S.%f>

The tool will print the needed fixes. Use option ``--fix`` to apply.


4. Adjust configuration files
-----------------------------

As always, the following settings might need further adjustments depending on
your previous setup.

.. note::

  Do not forget to add ".conf" suffix on apache's conf files.


Change gunicorn configuration file
""""""""""""""""""""""""""""""""""

Newer gunicorn drops support for ``django`` mode. You must update the gunicorn
configuration file (by default ``/etc/gunicorn.d/synnefo``) on all nodes to
``wsgi`` mode by changing the ``mode`` setting to use the Synnefo's wsgi
entry point and by adding ``synnefo.webproject.wsgi`` as the last item in the
``args`` list.

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

.. note::

  Since 0.19, Synnefo logs in a dedicated file ``/var/log/synnefo/synnefo.log``,
  separately from gunicorn's logs.


Update webserver's configuration file
"""""""""""""""""""""""""""""""""""""

Up until now, we used the ``X-Forwarded-Protocol = 'https'`` header to notify the
proxied django application that it was behind a secure proxy. This worked
because on gunicorn's version 0.9 a patch was introduced that specifically
looked for this header and value and adjusted the ``wsgi.url_scheme`` variable to
'https'. In gunicorn's 19 it now looks for headers defined in the ``secure_scheme_headers``
config variable which defaults to
``{ "X-FORWARDED-PROTOCOL": "ssl", "X-FORWARDED-PROTO": "https", "X-FORWARDED-SSL":"on"  }``.

You should change the header's key from ``X-FORWARDED-PROTOCOL`` to ``X-FORWARDED-PROTO``.


New ALLOWED_HOSTS setting
"""""""""""""""""""""""""

Since Django 1.5, the ``ALLOWED_HOSTS`` setting is required in production.
Synnefo v0.19 adds a default value for this setting to ``['*']`` which allows
all hosts. You can change this setting on each node to restrict the hosts that
Django is allowed to serve.


Update cache settings
"""""""""""""""""""""

In cyclades, you now have to set each one of the three caches in the Django's
cache framework format.

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
``LOCATION`` (e.g. ``127.0.0.1:11211``) as well. Check
`here <https://docs.djangoproject.com/en/1.7/topics/cache/>`_ for more
information.

Please adjust the new settings to match your previous setup. You might want to
remove settings like ``VMAPI_CACHE_BACKEND`` and ``CACHE_BACKEND`` that are
obsolete since 0.19.


Backend Allocator Module
""""""""""""""""""""""""

Synnefo v0.19 introduces a new FilterAllocator to replace the previous
DefaultAllocator module. Synnefo v0.19 uses the new module by default, unless
you have explicitly set the `BACKEND_ALLOCATOR_MODULE` in your settings. In that
case, it is advised to switch the setting value to the new default setting
`synnefo.logic.allocators.filter_allocator.FilterAllocator`. The default
filters include the newly introduced Project-Backend association policy, while
retaining the previous functionality for picking backends.


Re-register service and resource definitions
""""""""""""""""""""""""""""""""""""""""""""

The Cyclades service definition has been updated to exposed the 'image',
'network', and 'volume' endpoint URLs without a version suffix. It needs thus
to be registered again. On the Astakos node, run::

    astakos-host$ snf-component-register cyclades

This will detect that the Cyclades component is already registered and ask
to re-register. Answer positively. You need to enter the base URL and the UI
URL for Cyclades, just like during the initial registration.

.. note::

   You can run ``snf-manage component-list -o name,base_url,ui_url`` to
   inspect the currently registered base and UI URLs.


5. Reboot
---------

Reboot to finish the system upgrade. After reboot, services should
automatically start.
