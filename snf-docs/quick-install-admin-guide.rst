.. _quick-install-admin-guide:

Administrator's Quick Installation Guide
========================================

This the Administrator's quick installation guide.

It describes how to install Synnefo on a single physical node,
with minimum configuration. It installs Synnefo from Debian packages, and
assumes the node runs Debian Squeeze.

Prerequisites
-------------

Please make sure you already have the following:
 * A working installation of Ganeti on this node
 * A working installation of snf-image, with installed images. See
   https://code.grnet.gr/projects/snf-image/wiki for detailed info.
 * A DB server running PostgreSQL
 * A working deployment of RabbitMQ


Installation
------------

Install the following components from Debian packages.
Grab them from http://docs.dev.grnet.gr/debs/.

.. todo::

   Setup a source file for APT.
   The commands below install the needed dependencies manually,
   APT would take care of that.

.. todo::

   Document networking installation and configuration using
   ``grnet-vnode-tools``, ``nfdhcpd``

.. code-block:: console

   # apt-get install python python-setuptools
   # dpkg -i snf-common_0.7.4-1_all.deb
   # apt-get install python-django python-django-south
   # dpkg -i snf-webproject_0.7.4-1_all.deb
   # dpkg -i snf-pithos-lib_0.8.2-1_all.deb
   # dpkg -i snf-pithos-tools_0.8.2-1_all.deb
   # apt-get install python-sqlalchemy
   # dpkg -i snf-pithos-backend_0.8.2-1_all.deb
   # apt-get install python-daemon python-gevent
   # dpkg -i snf-vncauthproxy_1.1-1_all.deb
   # apt-get install python-simplejson python-pycurl python-dateutil
   # python-ipy python-crypto python-amqplib
   # dpkg -i snf-cyclades-app_0.7.4-1_all.deb
   # apt-get install python-pyinotify python-prctl nfdhcpd arptables
   # dpkg -i snf-cyclades-gtools_7.4-1_all.deb
   # dpkg -i snf-okeanos-site_7.4-1_all.deb


Configuration
--------------

Edit files under :file:`/etc/synnefo`, based on the location
of your Ganeti master, Postgres DB and RabbitMQ deployment.
At the very least you need to set sensible values for

 * ``BYPASS_AUTHENTICATION`` (set to True, for a test install)
 * ``GANETI_LINK_PREFIX``
 * ``GANETI_MASTER_IP``
 * ``GANETI_CLUSTER_INFO``
 * ``RABBIT_HOST``
 * ``RABBIT_USERNAME``
 * ``RABBIT_PASSWORD``
 * ``BYPASS_AUTHENTICATION_SECRET_TOKEN``
 * ``BACKEND_DB_MODULE``
 * ``BACKEND_DB_CONNECTION``
 * ``BACKEND_BLOCK_MODULE``
 * ``BACKEND_BLOCK_PATH``

.. todo::

   Document quick installation of Pithos, upload of Images.
