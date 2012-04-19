.. _dev-guide:

Synnefo Developer's Guide
^^^^^^^^^^^^^^^^^^^^^^^^^

This is the complete Synnefo Developer's Guide

Tying it all up with kamaki
===========================

kamaki
------

IM API (Astakos)
================

This is the Identity Management API:

.. toctree::
   :maxdepth: 2

   IM API <astakos-api-guide>

Compute API (Cyclades)
======================

This is the Cyclades Compute API:

.. toctree::
   :maxdepth: 2

   Compute API <cyclades-api-guide>

Network API (Cyclades)
======================

Network API body

Images API (Plankton)
=====================

Images API body

Storage API (Pithos+)
=====================

This is the Pithos+ File Storage API:

.. toctree::
   :maxdepth: 2

   File Storage API <pithos-api-guide>

Implementing new clients
========================

In this section we discuss implementation guidelines, that a developer should
take into account before writing his own client for the above APIs. Before,
starting your client implementation, make sure you have thoroughly read the
corresponding Synnefo API.

Pithos+ clients
---------------

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

Objects in Pithos+ can be:

 * Moved to trash and then deleted.
 * Shared with specific permissions.
 * Made public (shared with non-Pithos+ users).
 * Restored from previous versions.

Some of these functions are performed by the client software and some by the
Pithos+ server.

In the first version of Pithos, objects could also be assigned custom tags.
This is no longer supported. Existing deployments can migrate tags into a
specific metadata value, i.e. ``X-Object-Meta-Tags``.

Implementation Guidelines
~~~~~~~~~~~~~~~~~~~~~~~~~

Pithos+ clients should use the ``pithos`` and ``trash`` containers for active
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
 
::

  L: local state (stored state from last sync with the server)
  C: current state (state computed right before sync)
  S: server state

  if C == L:
      # No local changes
      if S == L:
          # No remote changes, nothing to do
      else:
          # Update local state to match that of the server
         L = S
  else:
      # We have local changes
      if S == L:
          # No remote changes, update the server
          S = C
          L = S
      else:
          # Both we and server have changes
          if C == S:
              # We were lucky, we did the same change
              L = S
          else:
              # We have conflicting changes
              resolve conflict

Notes:

 * States represent file hashes (it is suggested to use Merkle). Deleted or
   non-existing files are assumed to have a magic hash (e.g. empty string).
 * Updating a state (either local or remote) implies downloading, uploading or
   deleting the appropriate file.

Recommended Practices and Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assuming an authentication token is obtained, the following high-level
operations are available - shown with ``curl``:

* Get account information ::

    curl -X HEAD -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user

* List available containers ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user

* Get container information ::

    curl -X HEAD -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/pithos

* Add a new container ::

    curl -X PUT -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/test

* Delete a container ::

    curl -X DELETE -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/test

* List objects in a container ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/pithos

* List objects in a container (extended reply) ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/pithos?format=json

  It is recommended that extended replies are cached and subsequent requests
  utilize the ``If-Modified-Since`` header.

* List metadata keys used by objects in a container

  Will be in the ``X-Container-Object-Meta`` reply header, included in
  container information or object list (``HEAD`` or ``GET``). (**TBD**)

* List objects in a container having a specific meta defined ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/pithos?meta=favorites

* Retrieve an object ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/pithos/README.txt

* Retrieve an object (specific ranges of data) ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         -H "Range: bytes=0-9" \
         https://pithos.dev.grnet.gr/v1/user/pithos/README.txt

  This will return the first 10 bytes. To get the first 10, bytes 30-39 and the
  last 100 use ``Range: bytes=0-9,30-39,-100``.

* Add a new object (folder type) (**TBD**) ::

    curl -X PUT -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Type: application/directory" \
         https://pithos.dev.grnet.gr/v1/user/pithos/folder

* Add a new object ::

    curl -X PUT -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Type: text/plain" \
         -T EXAMPLE.txt
         https://pithos.dev.grnet.gr/v1/user/pithos/folder/EXAMPLE.txt

* Update an object ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Length: 10" \
         -H "Content-Type: application/octet-stream" \
         -H "Content-Range: bytes 10-19/*" \
         -d "0123456789" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt

  This will update bytes 10-19 with the data specified.

* Update an object (append) ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Length: 10" \
         -H "Content-Type: application/octet-stream" \
         -H "Content-Range: bytes */*" \
         -d "0123456789" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt

* Update an object (truncate) ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "X-Source-Object: /folder/EXAMPLE.txt" \
         -H "Content-Range: bytes 0-0/*" \
         -H "X-Object-Bytes: 0" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt

  This will truncate the object to 0 bytes.

* Add object metadata ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "X-Object-Meta-First: first_meta_value" \
         -H "X-Object-Meta-Second: second_meta_value" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt

* Delete object metadata ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "X-Object-Meta-First: first_meta_value" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt

  Metadata can only be "set". To delete ``X-Object-Meta-Second``, reset all
  metadata.

* Delete an object ::

    curl -X DELETE -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt

