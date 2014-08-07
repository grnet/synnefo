Cyclades Volumes
^^^^^^^^^^^^^^^^

This document describes the extension of Cyclades to handle block storage
devices, referred to as Volumes.


Current state and shortcomings
==============================

Currently one block storage device is created and destroyed together with the
virtual servers. One disk is created per server with the size and the disk
template that are described by the server's flavor. The disk is destroyed when
the server is destroyed. Also, There is no way to attach/detach disks to
existing servers and there is no API to expose information about the server's
disks.


Proposed changes
================

Cyclades will be able to manage volumes so that users can create volumes and
dynamically attach them to servers. Volumes can be created either empty or
filled with data from a specified source (image, volume or snapshot). Also,
users can dynamically remove volumes. Finally, a server can be created with
multiple volumes at once.


Implementation details
======================

Known Limitations
-----------------

While addition and removal of disks is supported by Ganeti, it is not supported
to handle disks that are not attached to an instance. There is no way to create
a disk without attaching it to an instance, neither a way to detach a disk from
an instance without deleting it. Future versions of Ganeti will make disks
separate entities, thus overcoming the above mentioned issues.  Until then,
this issues will also force a limitation to the way Cyclades will be handling
Volumes. Specifically, Cyclades volumes will not be attached/detached from
servers; they will be only be added and removed from them.

Apart from Ganeti's inability to manage disks as separate entities, attaching
and detaching a disk is not meaningful for storage solutions that are not
shared between Ganeti nodes and clusters, because this would require copying
the data of the disks between nodes. Thus, the ability to attach/detach a disk
will only be available for disks of externally mirrored template (EXT_MIRRORED
disk templates).

Also, apart from the root volume of an instance, initializing a volume with
data is currently only available for Archipelago volumes, since there is no
mechanism in Ganeti for filling data in other type of volumes (e.g. file, lvm,
drbd). Until then, creating a volume from a source, other than the root volume
of the instance, will only be supported for Archipelago.

Finally, an instance can not have disks of different disk template.

Cyclades internal representation
--------------------------------

Each volume will be represented by the new `Volume` database model, containing
information about the Volume, like the following:

* name: User defined name
* description: User defined description
* userid: The UUID of the owner
* size: Volume size in GB
* disk_template: The disk template of the volume
* machine: The server the volume is currently attached, if any
* source: The UUID of the source of the volume, prefixed by it's type, e.g. "snapshot:41234-43214-432"
* status: The status of the volume


Each Cyclades Volume corresponds to the disk of a Ganeti instance, uniquely
named `snf-vol-$VOLUME_ID`.

API extensions
--------------

The Cyclades API will be extended with all the needed operations to support
Volume management. The API will be compatible with OpenStack Cinder API.

Volume API
``````````

The new `volume` service will be implemented and will provide the basic
operations for volume management. This service provides the `/volumes` and
`/types` endpoints, almost as described in the OS Cinder API, with the only
difference that we will extend `POST /volumes/volumes` with a required
field to represent the server that the volume will be attached, and which is
named `server_id`.


Compute API extensions
``````````````````````

The API that is exposed by the `volume` service is enough for the addition and
removal of volumes to existing servers. However, it does not cover creating a
server from a volume or creating a server with more than one volumes. For this
reason, the `POST /servers` API call will be extended with the
`block_device_mapping_v2` attribute, as defined in the OS Cinder API, which is
a list of dictionaries with the following keys:

* source_type: The source of the volume (`volume` | `snapshot` | `image` | `blank`)
* uuid: The uuid of the source (if not blank)
* size: The size of the volume
* delete_on_termination: Whether to preserve the volume on instance deletion.

If the type is `volume`, then the volume that is specified by the `uuid` field
will be used. Otherwise, a new volume will be created which will contain the
data of the specified source (`image` or `snapshot`). If the source type
is `blank` then the new volume will be empty.

Also, we will implement `os_volume-attachments` extension, containing the
following operations:

* List server attachments(volumes)
* Show server attachment information
* Attach volume to server (notImplemented until Ganeti supports detachable volumes)
* Detach volume from server (notImplemented until Ganeti supports detachable volumes)

Quotas
------

The total size of volumes will be quotable, and will be directly mapped to
existing `cyclades.disk` resource. In the future, we may implement having
different quotas for each volume type.

Command-line interface
----------------------

The following management commands will be implemented:

* `volume-create`: Create a new volume
* `volume-remove`: Remove a volume
* `volume-list`: List volumes
* `volume-info`: Show volume details
* `volume-inspect`: Inspect volume in DB and Ganeti


The following commands will be extended:

* `server-create`: extended to specify server's volumes
* `server-inspect`: extended to display server's volumes
* `reconcile-servers`: extended to reconcile server's volumes
