.. _unify:

Storage Unification (Objects/Images/Snapshots/Volumes)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

| Synnefo proposes a completely unified approach for cloud storage.
| It uses the Archipelago storage system to implement the above idea.

In Synnefo:

* Objects (as seen by the Object Storage Service and managed via the Swift API)
* Images (as seen by the Image Service and managed via the Glance API)
* Snapshots (as seen by the Image Service and managed via the Glance API)

map to the `exact same` underlying virtual resource in the backend, which is an
Archipelago virtual resource. The only difference between them is a different
set of metadata that each service adds on the same underlying virtual resource.

Specifically, the Object Storage service adds Swift-specific metadata, the
Image Service adds Glance-specific metadata and the Volume service adds
Cinder-specific metadata. This means that one can have a user uploaded file
which is an Object on the Object Storage service and by just changing metadata
can register it as an Image on the Image service. And by changing metadata
again, one can convert it to a Snapshot, or vice-versa. The underlying virtual
resource stays intact and Archipelago doesn't even learn about upper layer
metadata, meaning that no real data gets moved or copied around during
conversions and registrations, and there is only one gateway to upload, sync
and download data to and from the cloud and this is the Object Storage service.


Relation between Objects, Images and Snapshots
==============================================

Objects, Images and Snapshots are the exact same things and map to the same,
single Archipelago virtual resource underneath. This Archipelago resource is a
read-only (RO) resource.

An Object represents all kinds of files that users would like to upload on an
Object Storage service, e.g., documents, videos, music, etc.

An Object that contains OS data (e.g., a raw disk dump), after getting uploaded
to the Object Storage service, it can be registered on the Image service, by
adding metadata to it, and then it becomes an Image, while still remaining an
Object for the Object Storage service. The metadata fall into two categories:

* Generic metadata
* Customization metadata

Generic metadata include name, creation-date, owner, size, id, checksum, etc.
and are mostly used for identification and presentation purposes by the Image
service. Customization metadata define the way this image will get customized
once its data finds their way on a bootable Volume (we describe how that
happens in the next section). Customization metadata configure: partitioning,
setting hostnames, setting passwords, resizing filesystem, injecting ssh keys,
etc.

If a registered Object (an Image) contains only Generic metadata and no
Customization metadata, i.e. having the 'EXCLUDE_ALL_TASKS' metadata property
set, then it is a Snapshot. A Snapshot's data will find their way on a bootable
or non-bootable Volume and this Volume will get attached to a VM as is, without
any customization afterwards.

So, one can convert a Snapshot to an Image by only changing its metadata and
vice-versa. Or convert it to a plain Object by just removing all metadata
(unregistering it from the Image service).


Volumes
=======

Volumes (the actual disks that get attached to and accessed by VMs) are
respectively mapped to Archipelago virtual resources in the backend, the same
way Objects, Images and Snapshots do. The only difference is that Volumes map
to read-write (RW) Archipelago resources.

Since Archipelago allows, among other things, thin cloning and snapshotting of
its virtual resources, and everything (Volumes/Objects/Images/Snapshots) is an
Archipelago resource in the backend, we can have workflows as the following:

[Archipelago resource] --- clone --> [New Archipelago RW resource]
[Archipelago resource] --- snapshot --> [New Archipelago RO resource]

which translate to:

[Image] --- clone --> [Volume] --- disk customization --> [Customized Volume] 
[Snapshot] --- clone --> [Volume]

[Volume] --- snapshot --> [Snapshot] --- customization metadata addition --> [Image]
[Volume] --- snapshot --> [Snapshot]


Conclusion
==========

In general we could say that Volumes are RW Archipelago resources exposed and
handled by the Volume service via the Cinder API and Images/Snapshots are RO
Archipelago resources exposed and handled by the Image service via the Glance
API. For Synnefo, Images and Snapshots are exact same things, with the only
difference that they have different customization metadata on the Image
service, where the first will get customized after they become Volumes, while
the latter will not get customized after they become Volumes. In the opposite
path, a Volume will always become a Snapshot first, and if added customization
metadata, will then become an Image.

Objects are also RO Archipelago resources exposed and handled by the Object
Storage service via the Swift API.

For a deeper dive in the internals of the above workflows please refer to the
:doc:`Snapshots <design/volume-snapshots>` and :doc:`Volumes <design/volumes>`
design documents.
