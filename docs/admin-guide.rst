.. _admin-guide:

Synnefo Administrator's Guide
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is the complete Synnefo Administrator's Guide.



General Synnefo Architecture
============================

The following graph shows the whole Synnefo architecture and how it interacts
with multiple Ganeti clusters. We hope that after reading the Administrator's
Guide you will be able to understand every component and all the interactions
between them. It is a good idea to first go through the Quick Administrator's
Guide before proceeding.

.. image:: images/synnefo-architecture1.png
   :width: 100%
   :target: _images/synnefo-architecture1.png


Identity Service (Astakos)
==========================


Overview
--------

Authentication methods
~~~~~~~~~~~~~~~~~~~~~~

Local Authentication
````````````````````

LDAP Authentication
```````````````````

.. _shibboleth-auth:

Shibboleth Authentication
`````````````````````````

Astakos can delegate user authentication to a Shibboleth federation.

To setup shibboleth, install package::

  apt-get install libapache2-mod-shib2

Change appropriately the configuration files in ``/etc/shibboleth``.

Add in ``/etc/apache2/sites-available/synnefo-ssl``::

  ShibConfig /etc/shibboleth/shibboleth2.xml
  Alias      /shibboleth-sp /usr/share/shibboleth

  <Location /im/login/shibboleth>
    AuthType shibboleth
    ShibRequireSession On
    ShibUseHeaders On
    require valid-user
  </Location>

and before the line containing::

  ProxyPass        / http://localhost:8080/ retry=0

add::

  ProxyPass /Shibboleth.sso !

Then, enable the shibboleth module::

  a2enmod shib2

After passing through the apache module, the following tokens should be
available at the destination::

  eppn # eduPersonPrincipalName
  Shib-InetOrgPerson-givenName
  Shib-Person-surname
  Shib-Person-commonName
  Shib-InetOrgPerson-displayName
  Shib-EP-Affiliation
  Shib-Session-ID

Finally, add 'shibboleth' in ``ASTAKOS_IM_MODULES`` list. The variable resides
inside the file ``/etc/synnefo/20-snf-astakos-app-settings.conf``

Architecture
------------

Prereqs
-------

Installation
------------

Configuration
-------------

Working with Astakos
--------------------

User activation methods
~~~~~~~~~~~~~~~~~~~~~~~

When a new user signs up, he/she is not marked as active. You can see his/her
state by running (on the machine that runs the Astakos app):

.. code-block:: console

   $ snf-manage user-list

There are two different ways to activate a new user. Both need access to a
running :ref:`mail server <mail-server>`.

Manual activation
`````````````````

You can manually activate a new user that has already signed up, by sending
him/her an activation email. The email will contain an approriate activation
link, which will complete the activation process if followed. You can send the
email by running:

.. code-block:: console

   $ snf-manage user-activation-send <user ID or email>

Be sure to have already setup your mail server and defined it in your Synnefo
settings, before running the command.

Automatic activation
````````````````````

FIXME: Describe Regex activation method

Astakos advanced operations
---------------------------

Adding "Terms of Use"
~~~~~~~~~~~~~~~~~~~~~

Astakos supports versioned terms-of-use. First of all you need to create an
html file that will contain your terms. For example, create the file
``/usr/share/synnefo/sample-terms.html``, which contains the following:

.. code-block:: console

   <h1>~okeanos terms</h1>

   These are the example terms for ~okeanos

Then, add those terms-of-use with the snf-manage command:

.. code-block:: console

   $ snf-manage term-add /usr/share/synnefo/sample-terms.html

Your terms have been successfully added and you will see the corresponding link
appearing in the Astakos web pages' footer.

Enabling reCAPTCHA
~~~~~~~~~~~~~~~~~~

Astakos supports the `reCAPTCHA <http://www.google.com/recaptcha>`_ feature.
If enabled, it protects the Astakos forms from bots. To enable the feature, go
to https://www.google.com/recaptcha/admin/create and create your own reCAPTCHA
key pair. Then edit ``/etc/synnefo/20-snf-astakos-app-settings.conf`` and set
the corresponding variables to reflect your newly created key pair. Finally, set
the ``ASTAKOS_RECAPTCHA_ENABLED`` variable to ``True``:

.. code-block:: console

   ASTAKOS_RECAPTCHA_PUBLIC_KEY = 'example_recaptcha_public_key!@#$%^&*('
   ASTAKOS_RECAPTCHA_PRIVATE_KEY = 'example_recaptcha_private_key!@#$%^&*('

   ASTAKOS_RECAPTCHA_ENABLED = True

Restart the service on the Astakos node(s) and you are ready:

.. code-block:: console

   # /etc/init.d/gunicorn restart

Checkout your new Sign up page. If you see the reCAPTCHA box, you have setup
everything correctly.



File Storage Service (Pithos)
=============================

Overview
--------

Architecture
------------

Prereqs
-------

Installation
------------

Configuration
-------------

Working with Pithos
-------------------

Pithos advanced operations
--------------------------



Compute/Network/Image Service (Cyclades)
========================================

Compute Overview
----------------

Network Overview
----------------

Image Overview
--------------

Architecture
------------

Prereqs
-------

RabbitMQ
~~~~~~~~

RabbitMQ is used as a generic message broker for Cyclades. It should be
installed on two seperate :ref:`QUEUE <QUEUE_NODE>` nodes in a high
availability configuration as described here:

    http://www.rabbitmq.com/pacemaker.html

The values set for the user and password must be mirrored in the ``RABBIT_*``
variables in your settings, as managed by :ref:`snf-common <snf-common>`.

.. todo:: Document an active-active configuration based on the latest version
   of RabbitMQ.

Installation
------------

Configuration
-------------

Working with Cyclades
---------------------

Cyclades advanced operations
----------------------------

Reconciliation mechanism
~~~~~~~~~~~~~~~~~~~~~~~~
On certain occasions, such as a Ganeti or RabbitMQ failure, the state of
Cyclades database may differ from the real state of VMs and networks in the
Ganeti backends. The reconciliation process is designed to synchronize
the state of the Cyclades DB with Ganeti. There are two management commands
for reconciling VMs and Networks

Reconciling VirtualMachine
~~~~~~~~~~~~~~~~~~~~~~~~~~
Reconciliation of VMs detects the following conditions:
 * Stale DB servers without corresponding Ganeti instances
 * Orphan Ganeti instances, without corresponding DB entries
 * Out-of-sync state for DB entries wrt to Ganeti instances

To detect all inconsistencies you can just run:
.. code-block:: console
  $ snf-manage reconcile --detect-all

Adding the `--fix-all` option, will do the actual synchronization:
.. code-block:: console
  $ snf-manage reconcile --detect-all --fix-all

Please see ``snf-manage reconcile --help`` for all the details.


Reconciling Networks
~~~~~~~~~~~~~~~~~~~~
Reconciliation of Networks detects the following conditions:
  * Stale DB networks without corresponding Ganeti networks
  * Orphan Ganeti networks, without corresponding DB entries
  * Private networks that are not created to all Ganeti backends
  * Unsynchronized IP pools

To detect all inconsistencies you can just run:
.. code-block:: console
  $ snf-manage reconcile-networks

Adding the `--fix-all` option, will do the actual synchronization:
.. code-block:: console
  $ snf-manage reconcile-networks --fix-all

Please see ``snf-manage reconcile-networks --help`` for all the details.


Block Storage Service (Archipelago)
===================================

Overview
--------

Architecture
------------

Prereqs
-------

Installation
------------

Configuration
-------------

Working with Archipelago
------------------------

Archipelago advanced operations
-------------------------------


.. _mail-server:

Configure mail server
---------------------

In order to be able to send email (for example activation emails),
synnefo needs access to a running mail server. Your mail server should
be defined in the ``/etc/synnefo/00-snf-common-admins.conf``
related constants. At least:

.. code-block:: console

   EMAIL_HOST = "my_mail_server.example.com"
   EMAIL_PORT = "25"

The "kamaki" API client
=======================

To upload, register or modify an image you will need the **kamaki** tool.
Before proceeding make sure that it is configured properly. Verify that
*image_url*, *storage_url*, and *token* are set as needed:

.. code-block:: console

   $ kamaki config list

To chage a setting use ``kamaki config set``:

.. code-block:: console

   $ kamaki config set image_url https://cyclades.example.com/plankton
   $ kamaki config set storage_url https://pithos.example.com/v1
   $ kamaki config set token ...

Upload Image
------------

As a shortcut, you can configure a default account and container that will be
used by the ``kamaki store`` commands:

.. code-block:: console

   $ kamaki config set storage_account images@example.com
   $ kamaki config set storage_container images

If the container does not exist, you will have to create it before uploading
any images:

.. code-block:: console

   $ kamaki store create images

You are now ready to upload an image. You can upload it with a Pithos+ client,
or use kamaki directly:

.. code-block:: console

   $ kamaki store upload ubuntu.iso

You can use any Pithos+ client to verify that the image was uploaded correctly.
The full Pithos URL for the previous example will be
``pithos://images@example.com/images/ubuntu.iso``.


Register Image
--------------

To register an image you will need to use the full Pithos+ URL. To register as
a public image the one from the previous example use:

.. code-block:: console

   $ kamaki glance register Ubuntu pithos://images@example.com/images/ubuntu.iso --public

The ``--public`` flag is important, if missing the registered image will not
be listed by ``kamaki glance list``.

Use ``kamaki glance register`` with no arguments to see a list of available
options. A more complete example would be the following:

.. code-block:: console

   $ kamaki glance register Ubuntu pithos://images@example.com/images/ubuntu.iso \
            --public --disk-format diskdump --property kernel=3.1.2

To verify that the image was registered successfully use:

.. code-block:: console

   $ kamaki glance list -l



Miscellaneous
=============

Admin tool: snf-manage
----------------------

``snf-manage`` is a tool used to perform various administrative tasks. It needs
to be able to access the django database, so the following should be able to
import the Django settings.

Additionally, administrative tasks can be performed via the admin web interface
located in /admin. Only users of type ADMIN can access the admin pages. To
change the type of a user to ADMIN, snf-admin can be used:

.. code-block:: console

   $ snf-manage user-modify 42 --type ADMIN

Logging
-------

Logging in Synnefo is using Python's logging module. The module is configured
using dictionary configuration, whose format is described here:

http://docs.python.org/release/2.7.1/library/logging.html#logging-config-dictschema

Note that this is a feature of Python 2.7 that we have backported for use in
Python 2.6.

The logging configuration dictionary is defined in settings.d/00-logging.conf
and is broken in 4 separate dictionaries:

  * LOGGING is the logging configuration used by the web app. By default all
    loggers fall back to the main 'synnefo' logger. The subloggers can be
    changed accordingly for finer logging control. e.g. To disable debug
    messages from the API set the level of 'synnefo.api' to 'INFO'.
  
  * DISPATCHER_LOGGING is the logging configuration of the logic/dispatcher.py
    command line tool.
  
  * SNFADMIN_LOGGING is the logging configuration of the snf-admin tool.
    Consider using matching configuration for snf-admin and the synnefo.admin
    logger of the web app.

Please note the following:

  * As of Synnefo v0.7, by default the Django webapp logs to syslog, the
    dispatcher logs to /var/log/synnefo/dispatcher.log and the console,
    snf-admin logs to the console.
  * Different handlers can be set to different logging levels:
    for example, everything may appear to the console, but only INFO and higher
    may actually be stored in a longer-term logfile



Scaling up to multiple nodes
============================

Here we will describe how to deploy all services, interconnected with each
other, on multiple physical nodes.

synnefo components
------------------

You need to install the appropriate synnefo software components on each node,
depending on its type, see :ref:`Architecture <cyclades-architecture>`.

Please see the page of each synnefo software component for specific
installation instructions, where applicable.

Install the following synnefo components:

Nodes of type :ref:`APISERVER <APISERVER_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-webproject <snf-webproject>`,
    :ref:`snf-cyclades-app <snf-cyclades-app>`
Nodes of type :ref:`GANETI-MASTER <GANETI_MASTER>` and :ref:`GANETI-NODE <GANETI_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-cyclades-gtools <snf-cyclades-gtools>`
Nodes of type :ref:`LOGIC <LOGIC_NODE>`
    Components
    :ref:`snf-common <snf-common>`,
    :ref:`snf-webproject <snf-webproject>`,
    :ref:`snf-cyclades-app <snf-cyclades-app>`.



Upgrade Notes
=============

Cyclades upgrade notes
----------------------

.. toctree::
   :maxdepth: 2

   cyclades-upgrade

Changelog
=========
