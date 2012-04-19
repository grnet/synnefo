.. _plankton:

Image Registry Service (plankton)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Introduction
============

Plankton is the synnefo Image Registry Service. It is implemented as a very thin
layer on top of Pithos+; every Image on Plankton is a file on a Pithos+ backend,
with special metadata. At the frontend, Plankton implements the OpenStack Glance
API; at the backend it queries an existing Pithos+ backend. In the current
implementation the service runs Plankton and Pithos+ on a single, unified
backend: users may synchronize their Images, using the Pithos+ clients, then
register them with Plankton, with zero data movement. Then spaw new VMs from 
those images with Cyclades.

.. image:: images/synnefo-clonepath.png

The :ref:`Plankton API <plankton-api-guide>` is implemented inside Cyclades, so please consult the
:ref:`Cyclades Documentation <cyclades>` for more details.

