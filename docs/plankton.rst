.. _plankton:

Image Registry Service
^^^^^^^^^^^^^^^^^^^^^^

Introduction
============

The Image Registry Service is a part of Cyclades. It is implemented as a very
thin layer on top of Pithos; every Image on the Image Service is a file on
Pithos, with special metadata which are stored on Cyclades. At the frontend,
Cyclades implement the OpenStack Glance API; at the backend it queries an
existing Pithos backend. In the current implementation the service runs the
Image Service and Pithos on a single, unified backend: users may synchronize
their Images, using the Pithos clients, then register them with Cyclades, with
zero data movement. Then spawn new VMs from those Images with Cyclades.

Let's see below:

.. image:: images/synnefo-clonepath.png

The figure shows a sailor bundling his physical machine with the
``snf-image-creator`` tool, uploading the file to Pithos, registering the file
as a new Image, and then spawning two new VMs with Cyclades from this Image.

The :ref:`Image API <plankton-api-guide>` is implemented inside Cyclades, so
please consult the :ref:`Cyclades Documentation <cyclades>` for more details.
