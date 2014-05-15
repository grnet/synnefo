====================
Volume snapshots
====================

The goal of this design document is to record and present the proposed method
for Volume snapshotting in Synnefo. We will describe the whole work-flow from
the user's API down to Archipelago and up again.

Snapshot functionality
=======================

The snapshot functionality aims to provide the user with the following:

a. A thin snapshot of an Archipelago volume: |br|
   The snapshot should capture the volume's data state at the time the
   snapshot was requested. |br|
   **Note:** The VM user is accountable for the consistency of its volume.
   Journaled filesystems or prior shutdown of the VM is advised.
#. Presenting the snapshot instantly as a regular file
   on Pithos: |br|
   Users can view their snapshots in Pithos as any other file that they have
   uploaded and can subsequently download them.
#. A registered Synnefo snapshot, ready to be deployed: |br|
   Essentially, if a snapshotted volume includes an OS installation, it can be
   used as any other Synnefo OS image. This allows users to create
   *restoration points* for their VMs.

Side goals
^^^^^^^^^^

In order to make the snapshot process as slim as possible, the following goals
must also be met:

a. Low computational/storage overhead: |br|
   If many users send snapshot requests, the service should be able to respond
   quick. Also, a snapshotted volume should not incur any significant storage
   overhead.
#. Solid reconciliation process: |br|
   If a snapshot request fails, the system should do the necessary cleanups or
   at least make it easy to reconcile the affected databases.

Snapshot creation
========================

An illustration of the proposed method follows below:

|create_snapshot|

Each step of the procedure is explained below:

#. The Cyclades App receives a snapshot request. The request is expected to
   originate from the user and be sent via an API client or the Cyclades UI. A
   valid snapshot request should target an existing volume ID.
#. The Cyclades App uses its Pithos Backend to create a `snapshot record`_ in
   the Pithos database. The snapshot record is explained in the following
   section.  It is initially set with the values that are seen in the diagram.
#. The Cyclades App creates a snapshot job and sends it to the Ganeti
   Master.
#. The Ganeti Master in turn, designates the snapshot job to the appropriate
   Ganeti Noded.
#. The Ganeti Noded runs the corresponding Archipelago ``ExtStorage`` script
   and invokes the Vlmc tool to create the snapshot.
#. The Vlmc tool instructs Archipelago to create a snapshot by sending a
   snapshot request.

Once Archipelago has (un)successfully created the snapshot, the response is
propagated to the Ganeti Master which in turn creates an event about this
snapshot job and its execution result.

7. snf-ganeti-eventd is informed about this event, using an ``inotify()``
   mechanism, and forwards it to the snf-dispatcher.
#. The snf-dispatcher uses its Pithos Backend to update the ``snapshot status``
   property of the snapshot record that was created in Step 2. According to the
   result of the snapshot request, the snapshot status is set as ``Ready`` or
   ``Error``. This means that, as far as Cinder is concerned, the snapshot is
   ready.
#. The ``Available`` attribute however is still ``0``. Swift (Pithos) will make
   it available (``1``) and thus usable, the first time it will try to ping
   back (a.k.a. the first time someone tries to access it).

Snapshot record
^^^^^^^^^^^^^^^^^

The snapshot record has the following attributes:

+-------------------+--------------------------------------+---------------+
| Key               | Value                                | Service       |
+===================+======================================+===============+
| file_name         | Generated (string - see below)       | Swift         |
+-------------------+--------------------------------------+---------------+
| available         | Generated (boolean)                  | Swift         |
+-------------------+--------------------------------------+---------------+

and the following properties:

+-------------------+--------------------------------------+---------------+
| Key               | Value                                | Service       |
+===================+======================================+===============+
| snapshot_name     | User-provided (string)               | Cinder        |
+-------------------+--------------------------------------+---------------+
| snapshot_status   | Generated (see Cinder API)           | Cinder        |
+-------------------+--------------------------------------+---------------+
| EXCLUDE_ALL_TASKS | Generated (string)                   | Glance        |
+-------------------+--------------------------------------+---------------+

The file_name is a string that has the following form::

        snf-snap-<vol_id>-<counter>

where:

* ``<vol_id>`` is the Volume ID and
* ``<counter>`` is the number of times that the volume has been snapshotted and
  increases monotonically.

The snapshot name should thus be unique.

"Available" attribute
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``available`` attribute is a Swift attribute that is introduced with
snapshots and applies to all Pithos files.  When a Pithos file is "available",
it means that its map file has been created and points to the correct data.
Normally, all Pithos files have their map file properly created before adding a
record in the Pithos database. Snapshots however are an exception to this rule,
since their map file is created asynchronously.

Therefore, the creation of a Pithos file has the following rules:

* If the file is a snapshot, the ``available`` attribute is set to "0".
* For all other files, the ``available`` attribute is set to "1".

**Note:** ``available`` can change from "0" to "1", but never the opposite.

The update of the ``available`` attribute happens implicitly after the creation
of the snapshot, when a request reads the file record from the
Pithos database. The following diagram shows how can a request (download
request for example) update the ``available`` attribute.

|available_attribute|

In short, what happens is:

#. The user asks to download the file from the Pithos App.
#. The Pithos App checks the file record and finds that the ``available``
   attribute is "0".
#. It then pings Archipelago to check the status of the map.
#. If the map exists, it sets ``available`` to "1" and can use the map file to
   serve the data.

VM creation from snapshot
===============================

The following diagram illustrates the VM creation process from a snapshot
image.

|spawn_from_snapshot|

The steps are explained in detail below:

#. A user who has the registered Images list (which includes all Snapshots
   too), requests to create a VM from the Cyclades App, using one of the
   registered snapshots of the list.
#. The Cyclades App sends a VM creation job to the Ganeti Master with the
   appropriate data. The data differ according to the disk template:

   * If the template is ext, then the "origin" field has the archipelago map
     name.
   * For any other template, the archipelago map name is passed in the "img_id"
     property of OS parameters.

#. The Ganeti Master designates the job to the appropriate Ganeti Noded.
#. The Ganeti Noded will create the disks, according to the requested disk
   template:

   a. If the disk template is "ext", the following execution path is taken:

      1. The Ganeti Noded runs the corresponding Archipelago ``ExtStorage``
         script and invokes the Vlmc tool.
      #. The Vlmc tool instructs Archipelago to create a volume from a
         snapshot.

   b. If the disk template is other than "ext", e.g. "drbd", Ganeti Noded
      creates a new, empty disk.

#. After the volume has been created, Ganeti Noded instructs snf-image to
   prepare it for deployment. The parameters that are passed to snf-image are
   the OS parameters of Step 2, and the main ones for each disk template are
   shown in the diagram, next to the "Ext?" decision box. According to the disk
   template, snf-image has two possible execution paths:

   a. If the disk template is "ext", there is no need to copy any data.
      Also, the image has the "EXCLUDE_ALL_TASKS" property set to "yes", so
      snf-image will run no customization scripts and will simply return.
   b. If the disk template is other than "ext", e.g. "drbd", snf-image will
      copy the snapshot's data from Pithos to the created DRBD disk. As above,
      since the image has the "EXCLUDE_ALL_TASKS" property set to "yes",
      snf-image will run no customization scripts.

.. |br| raw:: html

   <br />

.. |create_snapshot| image:: /images/create-snapshot.png

.. |available_attribute| image:: /images/available-attribute.png

.. |spawn_from_snapshot| image:: /images/spawn-from-snapshot.png

