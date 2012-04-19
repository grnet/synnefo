.. _archipelago:

Volume Service (archipelago)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Introduction
============

Every Volume inside a VM can be thought of as a linearly addressable set of
fixed-size blocks. The storage of the actual blocks is orthogonal to the task of
exposing a single block device for use by each VM. Bridging the gap between the
VMs performing random access to Volumes and the storage of actual blocks is
Archipelago: a custom storage handling layer which handled volumes as set of
distinct blocks in the backend, a process we call volume composition. For the
actual storage of blocks we are currently experimenting with RADOS, the
distributed object store underlying the Ceph parallel filesystem, to solve the
problem of reliable, fault-tolerant object storage through replication on
multiple storage nodes. Archipelago itself is agnostic to the actual block
storage backend. 

Archipelago is under active development and will be available soon.

