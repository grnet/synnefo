Welcome to synnefo's documentation
==================================

.. image:: /images/synnefo-logo.png

synnefo is opensource software used to create massively scalable IaaS clouds.

| You can see synnefo in action, powering GRNET's
  `~okeanos cloud service <https://okeanos.grnet.gr>`_.
| It is a collection of components (snf-*), most of them written in python, that
  are used as the building bricks to provide the following services:

.. toctree::
   :maxdepth: 1

   Compute Service (codename: cyclades) <cyclades>
   File Storage Service (codename: pithos+) <http://docs.dev.grnet.gr/pithos>
   Image Registry (codename: plankton) <http://docs.dev.grnet.gr/cyclades/plankton>
   Volume Storage Service (codename: archipelagos) <http://docs.dev.grnet.gr/archipelagos>
   Identity Management (codename: astakos) <http://docs.dev.grnet.gr/astakos>
   Billing Service (codename: aquarium) <http://docs.dev.grnet.gr/aquarium>

There are also components for:

.. toctree::
   :maxdepth: 1

   Secure image deployment (image tool) <snf-image>
   Command-line cloud management (kamaki tool) <http://docs.dev.grnet.gr/cyclades/kamaki>

synnefo is designed to be as simple, scalable and production ready as possible.
Furthermore, although it can be deployed in small configurations, its prime
target is large installations. If you are planning for the latter, you should
first be completely aware of what you want to provide, the architecture of your
cluster/s and synnefo's overall architecture before you start deploying.

All synnefo components use an intuitive settings mechanism, that gives you the
ability to either deploy the above services independently and standalone, or
interconnected with each other, in large configurations.

For complete documentation on each service's architecture, installation,
configuration, components needed, interfaces, APIs, and deployment follow the
above links. You can also browse all synnefo component in this list.

Quick Installation Guide
------------------------

A quick installation guide is provided, that describes how to install synnefo in
just one physical node for testing and development purposes. This guide is also
useful to those interested in deploying synnefo in large scale, as a starting
point that will help them get familiar with the synnefo components and overall
architecture. Such an installation, also provides a quick preview of the basic
synnefo features, although we would like to think that its real power will
unveil while scaling.

The quick installation guide comes in two versions:

| :ref:`Administrator's quick installation guide <quick-install-admin-guide>`
| This guide will walk you through a complete installation using debian packages.

| :ref:`Developer's quick installation guide <quick-install-devel-guide>`
| This guide will setup a development environment using pip install.

Standard Installation
---------------------

Also a complete standard installation guide will soon be available, that will
describe thoroughly how to deploy all services, interconnected with each other,
on multiple physical nodes.

Contact
-------

You can contact the synnefo team at: synnefo@lists.grnet.gr

Indices and tables
------------------


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
