.. _quick-install-guide:

Quick Installation Guide
^^^^^^^^^^^^^^^^^^^^^^^^

This is the Synnefo Quick Installation guide.

It describes how to install the whole Synnefo stack on one (1) physical node,
in less than 10 minutes. The installation uses the snf-deploy deployment tool
and installs on a physical node that runs Debian Squeeze. After successful
installation, you will have the following services running:

    * Identity Management (Astakos)
    * Object Storage Service (Pithos)
    * Compute Service (Cyclades)
    * Image Service (part of Cyclades)
    * Network Service (part of Cyclades)

and a single unified Web UI to manage them all.


Prerequisites
=============

To install Synnefo the only thing you need is a Debian Squeeze Base System that
has access to the public Internet.

Installation of snf-deploy
==========================

First of all we need to install the snf-deploy tool. To do so please add the
following line in your ``/etc/apt/sources.list`` file:

.. code-block:: console

   deb http://apt.dev.grnet.gr stable/

Then run:

.. code-block:: console

   # curl https://dev.grnet.gr/files/apt-grnetdev.pub | apt-key add -
   # apt-get update
   # apt-get install snf-deploy

Synnefo installation
====================

Now that you have `snf-deploy` successfully installed on your system, to install
the whole Synnefo stack run:

.. code-block:: console

   # snf-deploy all --autoconf

This might take a while depending on the physical host you are running on, since
it will download everything that is necessary, install and configure the whole
stack.

If the following ends without errors, you have successfully installed Synnefo.

Accessing the Synnefo installation
==================================

Remote access
-------------

If you want to access the Synnefo installation from a remote machine, please
first set your nameservers accordingly by adding the following line as your
first nameserver in ``/etc/resolv.conf``:

.. code-block:: console

   nameserver <IP>

The <IP> is the public IP of the machine that you deployed Synnefo on, and want
to access.

Then open a browser and point to:

`https://accounts.synnefo.live/im/`

Local access
------------

If you want to access the installation from the same machine it runs on, just
open a browser and point to:

`https://accounts.synnefo.live/im/`

The <domain> is automatically set to ``synnefo.live``. A local BIND is already
set up by `snf-deploy` to serve all FQDNs.

Login
-----

Once you see the Login screen, go ahead and login using:

| username: user@synnefo.org
| password: 12345

which is the default user. If you see the welcome screen, you have successfully
installed Synnefo on a single node.


Caveats
=======

Certificates
------------
To be able to view all web pages make sure you have accepted all certificates
for domains:

* synnefo.live
* accounts.synnefo.live
* cyclades.synnefo.live
* pithos.synnefo.live
* cms.synnefo.live


Spawning VMs
------------
By default, snf-deploy can't spawn VMs. To be able to do so, edit 
``/etc/synnefo/cyclades.conf`` and change line 29 from:

.. code-block:: console  
    
    'no_install': True,

to:

.. code-block:: console                                                         

    'no_install': False,  


Using the installation
======================

You should be able to:

* Spawn VMs from the one public Image that is already registered
* Upload files on Pithos
* Create Private Networks
* Connect VMs to Private Networks
* Upload new Images
* Register the new Images
* Spawn VMs from your new Images
* Use the kamaki command line client to access the REST APIs
