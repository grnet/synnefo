.. _admin-guide:

Synnefo Administrator's Guide
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is the complete Synnefo Administrator's Guide.

Quick Installation
==================

The quick installation guide describes how to install the whole synnefo stack
in just two physical nodes, for testing purposes. This guide is useful to those
interested in deploying synnefo in large scale, as a starting point that will
help them get familiar with the synnefo components and overall architecture, as
well as the interconnection between different services. Such an installation,
also provides a quick preview of the basic synnefo features, although we would
like to think that synnefo unveils its real power while scaling.

| :ref:`Administrator's quick installation guide <quick-install-admin-guide>`
| This guide will walk you through a complete installation using debian packages.

Common administrative tasks
===========================

If you installed Synnefo successfully and have a working deployment, here are
some common administrative tasks that you may find useful.


.. _user_activation:

User activation
---------------

When a new user signs up, he/she is not marked as active. You can see his/her
state by running (on the machine that runs the Astakos app):

.. code-block:: console

   $ snf-manage listusers

There are two different ways to activate a new user. Both need access to a
running mail server. Your mail server should be defined in the
``/etc/synnefo/00-snf-common-admins.conf`` related constants:

Manual activation
~~~~~~~~~~~~~~~~~

You can manually activate a new user that has already signed up, by sending
him/her an activation email. The email will contain an approriate activation
link, which will complete the activation process if followed. You can send the
email by running:

.. code-block:: console

   $ snf-manage sendactivation <user ID or email>

Be sure to have already setup your mail server and defined it in your synnefo
settings, before running the command.

Automatic activation
~~~~~~~~~~~~~~~~~~~~


The "kamaki" API client
-----------------------

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


Admin tool: snf-manage
----------------------

``snf-manage`` is a tool used to perform various administrative tasks. It needs
to be able to access the django database, so the following should be able to
import the Django settings.

Additionally, administrative tasks can be performed via the admin web interface
located in /admin. Only users of type ADMIN can access the admin pages. To change
the type of a user to ADMIN, snf-admin can be used:

.. code-block:: console

   $ snf-manage user modify 42 --type ADMIN

Reconciliation mechanism
------------------------

On certain occasions, such as a Ganeti or RabbitMQ failure, the VM state in the
system's database may differ from that in the Ganeti installation. The
reconciliation process is designed to bring the system's database in sync with
what Ganeti knows about each VM, and is able to detect the following three
conditions:

 * Stale DB servers without corresponding Ganeti instances
 * Orphan Ganeti instances, without corresponding DB entries
 * Out-of-sync operstate for DB entries wrt to Ganeti instances

The reconciliation mechanism runs as a management command, e.g., as follows:
[PYTHONPATH needs to contain the parent of the synnefo Django project
directory]:

.. code-block:: console

   $ export PYTHONPATH=/srv:$PYTHONPATH
   $ snf-manage reconcile --detect-all -v 2

Please see ``snf-manage reconcile --help`` for all the details.

The administrator can also trigger reconciliation of operating state manually,
by issuing a Ganeti ``OP_INSTANCE_QUERY_DATA`` command on a Synnefo VM, using
gnt-instance info.

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
other, on multiple physical nodes. For now, if you installed successfully using
the quick installation guide and need more details, please refer to each
component's own documentation.

Upgrade Notes
=============

Cyclades upgrade notes
----------------------

.. toctree::
   :maxdepth: 2

   cyclades-upgrade

Changelog
=========
