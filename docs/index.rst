Welcome to synnefo's documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: /images/synnefo-logo.png

synnefo is opensource software, used to create massively scalable IaaS clouds.

| You can see synnefo in action, powering GRNET's
  `~okeanos cloud service <https://okeanos.grnet.gr>`_.
| It is a collection of components (snf-*), most of them written in python, that
  are used as the building bricks to provide the following services:

.. toctree::
   :maxdepth: 1

   Identity Management (codename: astakos) <astakos>
   Object Storage Service (codename: pithos+) <pithos>
   Compute/Network Service (codename: cyclades) <cyclades>
   Image Registry (codename: plankton) <plankton>
   Billing Service (codename: aquarium) <http://docs.dev.grnet.gr/aquarium/latest/index.html>
   Volume Storage Service (codename: archipelago) <archipelago>

There are also components for:

.. toctree::
   :maxdepth: 1

   Secure image deployment (image tool) <snf-image>
   Command-line cloud management (kamaki tool) <http://docs.dev.grnet.gr/kamaki/v0.2/index.html>

synnefo is designed to be as simple, scalable and production ready as possible.
Furthermore, although it can be deployed in small configurations, its prime
target is large installations. If you are planning for the latter, you should
first be completely aware of what you want to provide, the architecture of your
cluster/s and synnefo's overall architecture before you start deploying.

All synnefo components use an intuitive settings mechanism, that gives you the
ability to either deploy the above services independently and standalone, or
interconnected with each other, in large configurations.


Synnefo Guides
==============

There are 3 guides for Synnefo. The Administrator's Guide targets system
administrators, who want to deploy synnefo on small or large installations. The
Developer's Guide targets developers, who want to build on top of synnefo and so
describes all the different types of interfaces synnefo provides to the external
world. The Integrator's Guide targets developers, who want to actually
extend/modify/change synnefo itself, so describes synnefo's indepth architecture
and the internals of synnefo components.

.. toctree::
   :maxdepth: 2

   Administrator's Guide <admin-guide>
   Developer's Guide <dev-guide>
   Integrator's Guide <intgrt-guide>


Contact
=======

You can contact the synnefo team at: synnefo@lists.grnet.gr


Indices and tables
==================


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
