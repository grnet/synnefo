Upgrade to Synnefo v0.14.10
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Synnefo v0.14.10 supports both Debian Squeeze and Wheezy. However, since
v0.14.10, Synnefo supports only Ganeti >= 2.8. This means that at least the
Ganeti nodes of a Synnefo deployment should run on Wheezy.

To upgrade to Synnefo v0.14.10 one needs to upgrade both Synnefo and Ganeti
during the same upgrade cycle, so some minimal service downtime is needed.
As always, VMs, Networks and Files will remain usable during the upgrade.

Since this is an upgrade to a minor version, no special upgrade operations
are needed except from the package upgrades.


1. Bring down the services
==========================

First, bring all services (Synnefo and Ganeti) down:

.. code-block:: console

   root@astakos-host# /etc/init.d/gunicorn stop
   root@cyclades-host# /etc/init.d/gunicorn stop
   root@pithos-host# /etc/init.d/gunicorn stop


   root@ganeti-master-host# /etc/init.d/ganeti stop
   root@ganeti-master-host# /etc/init.d/snf-ganeti-eventd stop
   root@ganeti-nodeX-host# /etc/init.d/ganeti stop

   root@cyclades-host# /etc/init.d/snf-dispatcher stop


2. Upgrade Ganeti
=================

Once, everything is stopped, upgrade Ganeti following the official upgrade notes
found here:

`Ganeti upgrade notes <http://docs.ganeti.org/ganeti/2.8/html/upgrade.html>`_

In a nutshell:

Install packages
----------------

Install the new Ganeti packages. To be able to use hotplug (which will be part
of the official Ganeti 2.10), we recommend using our Ganeti packages with
version: ``snf-ganeti=2.8.2+snapshot1+b64v1+hotplug+ippoolfix+rapifix-1~wheezy``

.. code-block:: console

   root@ganeti-master-host# apt-get install snf-ganeti ganeti-htools ganeti-haskell
   root@ganeti-nodeX-host# apt-get install snf-ganeti ganeti-htools ganeti-haskell

.. note:: Make sure you install all three Ganeti packages to all hosts.
          Also all packages should have the same version.

Upgrade
-------

Upgrade Ganeti's configuration (make sure you do all backup and dry-run steps as
described in the official guide):

.. code-block:: console

   root@ganeti-master-host# /usr/share/ganeti/cfgupgrade

Start Ganeti
------------

Start Ganeti and re-distribute the configuration to all Ganeti master candidates:

.. code-block:: console

   root@ganeti-master-host# /etc/init.d/ganeti start
   root@ganeti-nodeX-host# /etc/init.d/ganeti start

   root@ganeti-master-host# gnt-cluster redist-conf

   root@ganeti-master-host# /etc/init.d/ganeti stop
   root@ganeti-nodeX-host# /etc/init.d/ganeti stop


3. Upgrade Synnefo
==================

Install packages
----------------

Install the new v0.14.10 packages on all hosts according to your deployment.


4. Start all services
=====================

Once, everything is installed successfully, start all services
(Synnefo and Ganeti):

.. code-block:: console

   root@cyclades-host# /etc/init.d/snf-dispatcher start

   root@ganeti-master-host# /etc/init.d/snf-ganeti-eventd start

   root@ganeti-master-host# /etc/init.d/ganeti start
   root@ganeti-nodeX-host# /etc/init.d/ganeti start

   root@astakos-host# /etc/init.d/gunicorn start
   root@cyclades-host# /etc/init.d/gunicorn start
   root@pithos-host# /etc/init.d/gunicorn start
