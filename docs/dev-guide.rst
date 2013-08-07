.. _dev-guide:

Synnefo Developer's Guide
^^^^^^^^^^^^^^^^^^^^^^^^^

This is the complete Synnefo Developer's Guide. Here, we document all Synnefo
REST APIs, to allow external developers write independent tools that interact
with Synnefo.

Synnefo exposes the OpenStack APIs for all its operations. Also, extensions
have been written for advanced operations wherever needed, and minor changes
for things that were missing or change frequently.

Most Synnefo services have a corresponding OpenStack API:

| Cyclades/Compute Service -> OpenStack Compute API
| Cyclades/Network Service -> OpenStack Compute/Network API (not Quantum yet)
| Cyclades/Image Service -> OpenStack Glance API
| Pithos/Storage Service -> OpenStack Object Store API
| Astakos/Identity Service -> Proprietary, moving to OpenStack Keystone API
| Astakos/Quota Service -> Proprietary API
| Astakos/Resource Service -> Proprietary API

Below, we will describe all Synnefo APIs with conjuction to the OpenStack APIs.


Identity Service API (Astakos)
==============================

Currently, Astakos which is the Identity Management Service of Synnefo, has a
proprietary API, but we are moving to the OpenStack Keystone API.

The current Identity Management API is:

.. toctree::
   :maxdepth: 2

    Identity API <astakos-api-guide>


Resource and Quota Service API (Astakos)
========================================

.. toctree::
    :maxdepth: 2

    Resource and Quota API <quota-api-guide.rst>

Project API
===========

.. toctree::
    :maxdepth: 2

    Project API <project-api-guide.rst>

Compute Service API (Cyclades)
==============================

The Compute part of Cyclades exposes the OpenStack Compute API with minor
changes wherever needed.

This is the Cyclades/Compute API:

.. toctree::
   :maxdepth: 2

   Compute API <cyclades-api-guide>


Network Service API (Cyclades)
==============================

The Network Service is implemented inside Cyclades. It exposes the part of the
OpenStack Compute API that has to do with Networks. The OpenStack Quantum API
is not implemented yet.

Please consult the :ref:`Cyclades/Network API <cyclades-api-guide>` for more
details.


Image Service API (Cyclades)
============================

The Image Service is implemented inside Cyclades. It exposes the OpenStack
Glance API with minor changes wherever needed.

This is the Cyclades/Image API:

.. toctree::
   :maxdepth: 2

   Image API <plankton-api-guide>


Storage Service API (Pithos)
============================

Pithos is the Storage Service of Synnefo and it exposes the OpenStack Object
Storage API with extensions for advanced operations, e.g., syncing.

This is the Pithos Object Storage API:

.. toctree::
   :maxdepth: 2

   Object Storage API <pithos-api-guide>


Implementing new clients
========================

In this section we discuss implementation guidelines, that a developer should
take into account before writing his own client for the above APIs. Before,
starting your client implementation, make sure you have thoroughly read the
corresponding Synnefo API.

Pithos clients
--------------

User Experience
~~~~~~~~~~~~~~~

Hopefully this API will allow for a multitude of client implementations, each
supporting a different device or operating system. All clients will be able to
manipulate containers and objects - even software only designed for OOS API
compatibility. But a Pithos interface should not be only about showing
containers and folders. There are some extra user interface elements and
functionalities that should be common to all implementations.

Upon entrance to the service, a user is presented with the following elements -
which can be represented as folders or with other related icons:

 * The ``home`` element, which is used as the default entry point to the user's
   "files". Objects under ``home`` are represented in the usual hierarchical
   organization of folders and files.
 * The ``trash`` element, which contains files that have been marked for
   deletion, but can still be recovered.
 * The ``shared`` element, which contains all objects shared by the user to
   other users of the system.
 * The ``others`` element, which contains all objects that other users share
   with the user.
 * The ``groups`` element, which contains the names of groups the user has
   defined. Each group consists of a user list. Group creation, deletion, and
   manipulation is carried out by actions originating here.
 * The ``history`` element, which allows browsing past instances of ``home``
   and - optionally - ``trash``.

Objects in Pithos can be:

 * Moved to trash and then deleted.
 * Shared with specific permissions.
 * Made public (shared with non-Pithos users).
 * Restored from previous versions.

Some of these functions are performed by the client software and some by the
Pithos server.

In the first version of Pithos, objects could also be assigned custom tags.
This is no longer supported. Existing deployments can migrate tags into a
specific metadata value, i.e. ``X-Object-Meta-Tags``.

Implementation Guidelines
~~~~~~~~~~~~~~~~~~~~~~~~~

Pithos clients should use the ``pithos`` and ``trash`` containers for active
and inactive objects respectively. If any of these containers is not found, the
client software should create it, without interrupting the user's workflow. The
``home`` element corresponds to ``pithos`` and the ``trash`` element to
``trash``. Use ``PUT`` with the ``X-Move-From`` header, or ``MOVE`` to transfer
objects from one container to the other. Use ``DELETE`` to remove from
``pithos`` without trashing, or to remove from ``trash``. When moving objects,
detect naming conflicts with the ``If-Match`` or ``If-None-Match`` headers.
Such conflicts should be resolved by the user.

Object names should use the ``/`` delimiter to impose a hierarchy of folders
and files.

The ``shared`` element should be implemented as a read-only view of the
``pithos`` container, using the ``shared`` parameter when listing objects. The
``others`` element, should start with a top-level ``GET`` to retrieve the list
of accounts accessible to the user. It is suggested that the client software
hides the next step of navigation - the container - if it only includes
``pithos`` and forwards the user directly to the objects.

Public objects are not included in ``shared`` and ``others`` listings. It is
suggested that they are marked in a visually distinctive way in ``pithos``
listings (for example using an icon overlay).

A special application menu, or a section in application preferences, should be
devoted to managing groups (the ``groups`` element). All group-related actions
are implemented at the account level.

Browsing past versions of objects should be available both at the object and
the container level. At the object level, a list of past versions can be
included in the screen showing details or more information on the object
(metadata, permissions, etc.). At the container level, it is suggested that
clients use a ``history`` element, which presents to the user a read-only,
time-variable view of ``pithos`` contents. This can be accomplished via the
``until`` parameter in listings. Optionally, ``history`` may include ``trash``.

Uploading and downloading data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By using hashmaps to upload and download objects the corresponding operations
can complete much faster.

In the case of an upload, only the missing blocks will be submitted to the
server:

 * Calculate the hash value for each block of the object to be uploaded. Use
   the hash algorithm and block size of the destination container.
 * Send a hashmap ``PUT`` request for the object.

   * Server responds with status ``201`` (Created):

     * Blocks are already on the server. The object has been created. Done.

   * Server responds with status ``409`` (Conflict):

     * Server's response body contains the hashes of the blocks that do not
       exist on the server.
     * For each hash value in the server's response (or all hashes together):

       * Send a ``POST`` request to the destination container with the
         corresponding data.

 * Repeat hashmap ``PUT``. Fail if the server's response is not ``201``.

Consulting hashmaps when downloading allows for resuming partially transferred
objects. The client should retrieve the hashmap from the server and compare it
with the hashmap computed from the respective local file. Any missing parts can
be downloaded with ``GET`` requests with the additional ``Range`` header.

Syncing
~~~~~~~

Consider the following algorithm for synchronizing a local folder with the
server. The "state" is the complete object listing, with the corresponding
attributes.
 
.. code-block:: python

  # L: Local State, the last synced state of the object.
  # Stored locally (e.g. in an SQLite database)
  
  # C: Current State, the current local state of the object
  # Returned by the filesystem
  
  # S: Server State, the current server state of the object
  # Returned by the server (HTTP request)
  
  def sync(path):
      L = get_local_state(path)   # Database action
      C = get_current_state(path) # Filesystem action
      S = get_server_state(path)  # Network action
  
      if C == L:
          # No local changes
          if S == L:
              # No remote changes, nothing to do
              return
          else:
              # Update local state to match that of the server
              download(path)
              update_local_state(path, S)
      else:
          # Local changes exist
          if S == L:
              # No remote changes, update the server and the local state
              upload(path)
              update_local_state(path, C)
          else:
              # Both local and server changes exist
              if C == S:
                  # We were lucky, both did the same
                  update_local_state(path, C)
              else:
                  # Conflicting changes exist
                  conflict()
  

Notes:

 * States represent file hashes (it is suggested to use Merkle). Deleted or
   non-existing files are assumed to have a magic hash (e.g. empty string).
