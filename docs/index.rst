Welcome to Synnefo's documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: /images/synnefo-logo.png

Synnefo is a complete open source cloud stack written in Python that provides
Compute, Network, Image, Volume and Storage services, similar to the ones
offered by AWS. Synnefo manages multiple `Ganeti
<http://code.google.com/p/ganeti>`_ clusters at the backend for handling of
low-level VM operations. To boost 3rd-party compatibility, Synnefo exposes the
OpenStack APIs to users.

You can see Synnefo in action, powering GRNET's
`~okeanos public cloud service <http://okeanos.grnet.gr>`_.

Synnefo has three main components providing the corresponding services:

.. toctree::
   :maxdepth: 1

   Astakos: Identity/Account services <astakos>
   Pithos: File/Object Storage service <pithos>
   Cyclades: Compute/Network/Image/Volume services <cyclades>

There are also the following tools:

.. toctree::
   :maxdepth: 1

   kamaki: Command-line client <http://www.synnefo.org/docs/kamaki/latest/index.html>
   snf-deploy: Synnefo deployment tool <snf-deploy>
   snf-image-creator: Image bundling/uploading/registering tool <http://www.synnefo.org/docs/snf-image-creator/latest/index.html>
   snf-image: Secure image deployment tool <snf-image>
   snf-burnin: Integration testing tool for a running Synnefo deployment <snf-burnin>

This is an overview of the Synnefo services:

.. image:: images/synnefo-overview.png
   :target: _images/synnefo-overview.png

Synnefo is designed to be as simple, scalable and production ready as possible.
Furthermore, although it can be deployed in small configurations, its prime
target is large installations.

All Synnefo components use an intuitive settings mechanism, that adds and removes
settings dynamically as components are getting added or removed from a physical
node. All settings are stored in a single location.

.. _general-arch:

Synnefo General Architecture
============================

The following graph shows the whole Synnefo architecture and how it interacts
with multiple Ganeti clusters.

.. image:: images/synnefo-arch2.png
   :width: 100%
   :target: _images/synnefo-arch2.png

Synnefo also supports RADOS as an alternative storage backend for
Files/Images/VM disks. :ref:`Here <syn+archip+rados>` is a graph that shows
Synnefo running with two different storage backends.

Synnefo Guides
==============

There are 4 guides for Synnefo.

The Quick Installation guide describes how to install Synnefo on a single node
in less than 10 minutes using the `snf-deploy` tool. This kind of installation
is targeted for testing and demo environments rather than production usage
deployments. It is the perfect way, even for an inexperienced user to have the
whole Synnefo stack up and running and allows for a quick preview of the basic
Synnefo features.

The Admin's installation guide describes how to install the whole Synnefo stack
in just two physical nodes. This guide is useful to those interested in
deploying Synnefo in large scale, as a starting point that will help them get
familiar with the Synnefo components and overall architecture, as well as the
interconnection between different services. This guide explains the whole
procedure step by step, without the use of the `snf-deploy` tool. Anyone
familiar with this guide, will be able to easily install Synnefo in a larger
number of nodes too, or even expand the two node installation dynamically.

The Administrator's Guide targets system administrators, who want to dive into
more details and common tasks regarding Synnefo. For the experienced Synnefo
administrator, there is also a section that describes how to do scale-out
Synnefo deployments with corresponding examples. This targets large scale
installations of Synnefo.

The Developer's Guide targets developers, who want to build on top of Synnefo
and so describes all the different types of interfaces Synnefo provides to the
external world. Also documents all Synnefo external REST APIs.

.. The Integrator's Guide targets developers, who want to actually
.. extend/modify/change Synnefo itself, so describes Synnefo's indepth
.. architecture and the internals of Synnefo components (currently out-of-date!).


.. toctree::
   :maxdepth: 1

   Quick Installation Guide (single node) <quick-install-guide>
   Installation Guide (on two nodes) <quick-install-admin-guide>

.. toctree::
   :maxdepth: 2

   Administrator's Guide <admin-guide>
   Developer's Guide <dev-guide>


List of all Synnefo components
==============================

They are also available from our apt repository: ``apt.dev.grnet.gr``

 * `snf-common <http://www.synnefo.org/docs/snf-common/latest/index.html>`_
 * `snf-webproject <http://www.synnefo.org/docs/snf-webproject/latest/index.html>`_
 * `snf-astakos-app <http://www.synnefo.org/docs/astakos/latest/index.html>`_
 * `snf-pithos-backend <http://www.synnefo.org/docs/pithos/latest/backends.html>`_
 * `snf-pithos-app <http://www.synnefo.org/docs/pithos/latest/index.html>`_
 * `snf-pithos-webclient <http://www.synnefo.org/docs/pithos-webclient/latest/index.html>`_
 * `snf-cyclades-app <http://www.synnefo.org/docs/snf-cyclades-app/latest/index.html>`_
 * `snf-cyclades-gtools <http://www.synnefo.org/docs/snf-cyclades-gtools/latest/index.html>`_
 * `astakosclient <http://www.synnefo.org/docs/astakosclient/latest/index.html>`_
 * `snf-vncauthproxy <https://code.grnet.gr/projects/vncauthproxy>`_
 * `snf-image <https://code.grnet.gr/projects/snf-image/wiki/>`_ 
 * `snf-image-creator <http://www.synnefo.org/docs/snf-image-creator/latest/index.html>`_
 * `snf-occi <http://www.synnefo.org/docs/snf-occi/latest/index.html>`_
 * `snf-cloudcms <http://www.synnefo.org/docs/snf-cloudcms/latest/index.html>`_
 * `nfdhcpd <https://code.grnet.gr/projects/nfdhcpd>`_


Design
======

Drafts
------

.. toctree::
   :maxdepth: 1

   Sample design <design/sample>


Contact
=======

You can contact the Synnefo team at the following mailing lists:

 * Users list: synnefo@googlegroups.com
 * Developers list: synnefo-devel@googlegroups.com

The official site is:

 `http://www.synnefo.org <http://www.synnefo.org>`_

Indices and tables
==================


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
