Welcome to Synnefo's documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: /images/synnefo-logo.png

| Synnefo is open source cloud software, used to create massively scalable IaaS
  clouds.
| Synnefo uses `Google Ganeti <http://code.google.com/p/ganeti/>`_ for the low
  level VM management part.

| You can see Synnefo in action, powering GRNET's
  `~okeanos public cloud service <http://okeanos.io>`_.
| It is a collection of components (snf-*), most of them written in python, that
  are used as the building bricks to provide the following services:

.. toctree::
   :maxdepth: 1

   Identity Management (codename: astakos) <astakos>
   Object Storage Service (codename: pithos+) <pithos>
   Compute Service (codename: cyclades) <cyclades>
   Network Service (part of Cyclades) <networks>
   Image Registry (codename: plankton) <plankton>
   Billing Service (codename: aquarium) <http://docs.dev.grnet.gr/aquarium/latest/index.html>
   Volume Storage Service (codename: archipelago) <archipelago>

.. image:: images/synnefo-overview.png

There are also components for:

.. toctree::
   :maxdepth: 1

   Secure image deployment (snf-image tool) <snf-image>
   Command-line cloud management (kamaki tool) <http://docs.dev.grnet.gr/kamaki/latest/index.html>
   Image bundling/uploading/registering (snf-image-creator tool) <http://docs.dev.grnet.gr/snf-image-creator/latest/index.html>

Synnefo is designed to be as simple, scalable and production ready as possible.
Furthermore, although it can be deployed in small configurations, its prime
target is large installations. If you are planning for the latter, you should
first be completely aware of what you want to provide, the architecture of your
cluster/s and Synnefo's overall architecture before you start deploying.

All Synnefo components use an intuitive settings mechanism, that gives you the
ability to either deploy the above services independently and standalone, or
interconnected with each other, in large configurations.


Synnefo General Architecture
============================

The following graph shows the whole Synnefo architecture and how it interacts
with multiple Ganeti clusters. Right click on the image and select "Open image
in new tab" to be able to zoom in.

.. image:: images/synnefo-architecture1.png
   :width: 800px


Synnefo Guides
==============

There are 4 guides for Synnefo.

The quick installation guide describes how to install the whole synnefo stack
in just two physical nodes, for testing purposes. This guide is useful to those
interested in deploying synnefo in large scale, as a starting point that will
help them get familiar with the synnefo components and overall architecture, as
well as the interconnection between different services. Such an installation,
also provides a quick preview of the basic synnefo features, although we would
like to think that synnefo unveils its real power while scaling.

The Administrator's Guide targets system administrators, who want to dive into
more details and common tasks regarding Synnefo. The Developer's Guide targets
developers, who want to build on top of Synnefo and so describes all the
different types of interfaces Synnefo provides to the external world. The
Integrator's Guide targets developers, who want to actually
extend/modify/change Synnefo itself, so describes Synnefo's indepth
architecture and the internals of Synnefo components.

.. toctree::
   :maxdepth: 1

   Quick Installation Guide <quick-install-admin-guide>

.. toctree::
   :maxdepth: 2

   Administrator's Guide <admin-guide>
   Developer's Guide <dev-guide>
   Integrator's Guide <intgrt-guide>


List of all Synnefo components
==============================

Here are all Synnefo components. Combined in different ways, they provide all
Synnefo services. All components are released as:

.. toctree::

   debian packages <http://docs.dev.grnet.gr/debs/>
   python packages <http://docs.dev.grnet.gr/pypi/>

They are also available from our apt repository: ``apt.okeanos.grnet.gr``

 * `snf-common <http://docs.dev.grnet.gr/snf-common/latest/index.html>`_
 * `snf-webproject <http://docs.dev.grnet.gr/snf-webproject/latest/index.html>`_
 * `snf-astakos-app <http://docs.dev.grnet.gr/astakos/latest/index.html>`_
 * `snf-pithos-backend <http://docs.dev.grnet.gr/pithos/latest/backends.html>`_
 * `snf-pithos-app <http://docs.dev.grnet.gr/pithos/latest/index.html>`_
 * `snf-pithos-tools <http://docs.dev.grnet.gr/pithos/latest/index.html>`_
 * `snf-pithos-webclient <http://docs.dev.grnet.gr/pithos-webclient/latest/index.html>`_
 * `snf-cyclades-app <http://docs.dev.grnet.gr/snf-cyclades-app/latest/index.html>`_
 * `snf-cyclades-gtools <http://docs.dev.grnet.gr/snf-cyclades-gtools/latest/index.html>`_
 * `snf-vncauthproxy <https://code.grnet.gr/projects/vncauthproxy>`_
 * `snf-image <https://code.grnet.gr/projects/snf-image/wiki/>`_ 
 * `snf-image-creator <http://docs.dev.grnet.gr/snf-image-creator/latest/index.html>`_
 * `snf-occi <http://docs.dev.grnet.gr/snf-occi/latest/index.html>`_
 * `snf-cloudcms <http://docs.dev.grnet.gr/snf-cloudcms/latest/index.html>`_
 * `nfdhcpd <https://code.grnet.gr/projects/nfdhcpd>`_


Contact
=======

You can contact the Synnefo team at the following mailing lists:

 * Users list: synnefo@googlegroups.com
 * Developers list: synnefo-devel@googlegroups.com

Indices and tables
==================


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
