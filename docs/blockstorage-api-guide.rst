.. _blockstorage-api-guide:

API Guide
*********

:ref:`Cyclades <cyclades>` include the Block Storage Service of
`Synnefo <http://www.synnefo.org>`_. The Cyclades/Block Storage API complies
with
`OpenStack Block Storage <http://developer.openstack.org/api-ref-blockstorage-v2.html>`_
version 2, with custom extensions when needed.

This document's goals are:

* Define the Cyclades/Block Storage REST API
* Clarify the differences between Cyclades and OpenStack/Block Storage

Users and developers who wish to access Cyclades through its REST API are
advised to use the
`kamaki <http://www.synnefo.org/docs/kamaki/latest/index.html>`_ command-line
client and the associated python library, instead of making direct calls.

General API Information
=======================

Authentication
--------------

All requests use the same authentication method: an ``X-Auth-Token`` header is
passed to the service, which is used to authenticate the user and retrieve user
related information. No other user details are passed through HTTP.


API Operations
==============

.. rubric:: Volumes

==================================== =============================== ====== ======== ==========
Description                          URI                             Method Cyclades OS/Block Storage
==================================== =============================== ====== ======== ==========
`List <#list-volumes>`_              ``/volumes``                    GET    ✔        ✔
\                                    ``/volumes/detail``             GET    ✔        ✔
`Create <#create-volume>`_           ``/volumes``                    POST   ✔        ✔
`Get Details <#get-volume-details>`_ ``/volumes/<volume id>``        GET    ✔        ✔
`Update <#update-volume>`_           ``/volumes/<volume id>``        PUT    ✔        ✔
`Delete <#delete-volume>`_           ``/volumes/<volume id>``        DELETE ✔        ✔
`Reassign <#reassign-volume>`_       ``/volumes/<volume id>/action`` POST   ✔        **✘**
==================================== =============================== ====== ======== ==========

.. rubric:: Snapshots

====================================== ============================ ====== ======== ==========
Description                            URI                          Method Cyclades OS/Block Storage
====================================== ============================ ====== ======== ==========
`List <#list-snapshots>`_              ``/snapshots``               GET    ✔        ✔
\                                      ``/snapshots/detail``        GET    ✔        ✔
`Create <#create-snapshot>`_           ``/snapshots``               POST   ✔        ✔
`Get Details <#get-snapshot-details>`_ ``/snapshots/<snapshot id>`` GET    ✔        ✔
`Update <#update-snapshot>`_           ``/snapshots/<snapshot id>`` PUT    ✔        ✔
`Delete <#delete-snapshot>`_           ``/snapshots/<snapshot id>`` DELETE ✔        ✔
====================================== ============================ ====== ======== ==========

.. rubric:: Volume types

========================================= ================================== ====== ======== ==========
Description                               URI                                Method Cyclades OS/Block Storage
========================================= ================================== ====== ======== ==========
`List <#list-volume-types>`_              ``/volume-types``                  GET    ✔        ✔
`Get Details <#get-volume-type-details>`_ ``/volume-types/<volume-type id>`` GET    ✔        ✔
========================================= ================================== ====== ======== ==========

List Volumes
------------

List all volumes owned by the user.

.. rubric:: Request

=================== ====== ======== ==========
URI                 Method Cyclades OS/Block Storage
=================== ====== ======== ==========
``/volumes``        GET    ✔        ✔
``/volumes/detail`` GET    ✔        ✔
=================== ====== ======== ==========

* Both requests return a list of volumes. The first returns just ``id``,
  ``display_name`` and ``links``, while the second returns the
  `full collection <#volume-ref>`_ of volume attributes

|
============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
============== ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
401 (Unauthorized)          Missing or expired user token
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================

|

Response body contents::

  volumes: [
    {
      <volume attribute>: <value>,
      ...
    }, ...
  ]

The volume attributes are listed `here <#volume-ref>`_

*Example List Volumes: JSON (regular)*

.. code-block:: javascript

  GET https://example.org/cyclades/v2/volumes

  {
    "volumes": [
      {
        "links": [
          {
            "href": "https://example.org/cyclades/v2/volumes/42",
            "rel": "self"
          }, {
            "href": "https://example.org/cyclades/v2/volumes/42",
            "rel": "bookmark"
          }
        ],
        "id": "42",
        "display_name": "Volume One",
      }, {
        "links": [
          {
            "href": "https://example.org/cyclades/v2/volumes/43",
            "rel": "self"
          }, {
            "href": "https://example.org/cyclades/v2/volumes/43",
            "rel": "bookmark"
          }
        ],
        "id": "43",
        "display_name": "Volume Two",
      }
    ]
  }

*Example List Volumes: JSON (detail)*

.. code-block:: javascript

  GET https://example.org/cyclades/v2/volumes/detail

  {
    "volumes": [
      {
        "links": [
          {
            "href": "https://example.org/cyclades/v2/volumes/42",
            "rel": "self"
          }, {
            "href": "https://example.org/cyclades/v2/volumes/42",
            "rel": "bookmark"
          }
        ],
        "id": "42",
        "display_name": "Volume One",
        "status": "AVAILABLE",
        "size": 2,
        "display_description": "The First Volume",
        "created_at": "2014-02-21T19:52:04.949734",
        "metadata": {},
        "snapshot_id": null,
        "source_volid": null,
        "image_id": null,
        "attachments": [],
        "volume_type": 1,
        "delete_on_termination": True,
        "project": "1234"
      }, {
        "links": [
          {
            "href": "https://example.org/cyclades/v2/volumes/43",
            "rel": "self"
          }, {
            "href": "https://example.org/cyclades/v2/volumes/43",
            "rel": "bookmark"
          }
        ],
        "id": "43",
        "display_name": "Volume Two",
        "status": "AVAILABLE",
        "size": 3,
        "display_description": "The Second Volume",
        "created_at": "2014-03-21T19:52:04.949734",
        "metadata": {"requested_by": "John"},
        "snapshot_id": null,
        "source_volid": null,
        "image_id": null,
        "attachments": [],
        "volume_type": 2,
        "delete_on_termination": False,
        "project": "1234"
      },
    ]
  }

Get Volume Details
------------------

This operation returns detailed information for a volume

.. rubric:: Request

======================== ====== ======== ==========
URI                      Method Cyclades OS/Block Storage
======================== ====== ======== ==========
``/volumes/<volume id>`` GET    ✔        ✔
======================== ====== ======== ==========

|

============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
============== ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed volume id
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Volume not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

|

Response body contents::

  volume: {
    <volume attribute>: <value>,
    ...
  }

Volume attributes are explained `here <#volume-ref>`_

*Example Get Volume Response*

.. code-block:: javascript

  GET https://example.org/cyclades/v2/volumes/44

  {
    "volume": {
      "links": [
        {
          "href": "https://example.org/cyclades/v2/volumes/44",
          "rel": "self"
        }, {
          "href": "https://example.org/cyclades/v2/volumes/44",
          "rel": "bookmark"
        }
      ],
      "id": "44",
      "display_name": "Volume Three",
      "status": "CREATING",
      "size": 10,
      "display_description": null,
      "created_at": "2014-05-13T19:52:04.949734",
      "metadata": {},
      "snapshot_id": null,
      "source_volid": null,
      "image_id": null,
      "attachments": [],
      "volume_type": 2,
      "delete_on_termination": False,
      "project": "1234"
    }
  }

Create Volume
-------------

Create a new volume

.. rubric:: Request

============ ====== ======== ==========
URI          Method Cyclades OS/Block Storage
============ ====== ======== ==========
``/volumes`` POST   ✔        ✔
============ ====== ======== ==========

|
============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
Content-Type   Type or request body      required required
Content-Length Length of request body    required required
============== ========================= ======== ==========

Request body contents::

  volume: {
      <volume attribute>: <value>,
      ...
  }

=================== ================================ ======== ================
Volume Attribute    Value                            Cyclades OS/Block Storage
=================== ================================ ======== ================
size                Volume size in GB                required required
server_id           An existing VM to create from    ✔*       **✘**
availability_zone   Respond in xml                   **✘**    ✔
source_volid        Existing volume to create from   **✘**    ✔
display_description A description                    ✔        ✔
snapshot_id         Existing snapshot to create from ✔        ✔
display_name        The name                         required ✔
imageRef            Image to create from             ✔        ✔
volume_type         The associated volume type       ✔        ✔
bootable            Whether the volume is bootable   **✘**    ✔
metadata            Key-Value metadata pairs         ✔        ✔
project             Assigned project for quotas      ✔        **✘**
=================== ================================ ======== ================

.. note::

  * ``server_id`` is required for non-detachable volumes

*Example Create Volume Request: JSON*

.. code-block:: javascript

  POST https://example.org/cyclades/v2/volumes

  {
    "volume": {
      "size": 10,
      "display_name": "Volume Three",
      "server_id": "117",
      "volume_type": 1,
    }
  }

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
202 (OK)                    Request succeeded
400 (Bad Request)           Malformed request data
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Resource (server_id, imageRef, etc,) not found
413 (Over Limit)            Exceeded some resource limit
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

|

Response body contents::

  volume: {
    <volume attribute>: <value>,
    ...
  }

Volume attributes are `listed here <#server-ref>`_.

*Example Create Volume Response: JSON*

.. code-block:: javascript

  {
    "volume": {
      "links": [
        {
          "href": "https://example.org/cyclades/v2/volumes/44",
          "rel": "self"
        }, {
          "href": "https://example.org/cyclades/v2/volumes/44",
          "rel": "bookmark"
        }
      ],
      "id": "44",
      "display_name": "Volume Three",
      "status": "CREATING",
      "size": 10,
      "display_description": null,
      "created_at": "2014-05-13T19:52:04.949734",
      "metadata": {},
      "snapshot_id": null,
      "source_volid": null,
      "image_id": null,
      "attachments": [],
      "volume_type": 1,
      "delete_on_termination": True,
      "project": "1234"
    }
  }

Update Volume
-------------

.. rubric:: Response

======================== ====== ======== ==========
URI                      Method Cyclades OS/Block Storage
======================== ====== ======== ==========
``/volumes/<volume id>`` PUT    ✔        ✔
======================== ====== ======== ==========

|
============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
Content-Type   Type or request body      required required
Content-Length Length of request body    required required
============== ========================= ======== ==========

Request body contents::

  volume: {
    <volume attribute>: <value>,
    ...
  }

===================== ===================== ======== ==========
Attribute             Description           Cyclades OS/Block Storage
===================== ===================== ======== ==========
display_name          Server name           ✔        ✔
display_description   Descrition            ✔        ✔
delete_on_termination Switch this attribute ✔        **✘**
===================== ===================== ======== ==========

*Example Rename Server Request: JSON*

.. code-block:: javascript

  POST https://example.org/cyclades/v2/volumes/42

  {"volume": {"display_name": "New name"}}

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Volume not found
409 (Build In Progress)     Volume is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

Response body contents::

  volume: {
    <volume attribute>: <value>,
    ...
  }

Volume attributes are explained `here <#volume-ref>`_

*Example update volume Response*

.. code-block:: javascript

  {
    "volume": {
      "id": "42",
      "display_name": "New Name",
      ...
    }
  }

Update Volume Metadata
----------------------

.. rubric:: Response

================================= ======== ======== ==========
URI                               Method   Cyclades OS/Block Storage
================================= ======== ======== ==========
``/volumes/<volume id>/metadata`` POST/PUT    ✔        ✔
================================= ======== ======== ==========

* POST will create new metadata for the specified Volume if the key doesn't
  exist, while it will update metadata for which the key already exists.
* PUT will delete any old existing metadata and it'll replace them with
  the ones specified in the request.

============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
Content-Type   Type or request body      required required
Content-Length Length of request body    required required
============== ========================= ======== ==========

Request body contents::

  volume: {
    <key>: <value>,
    ...
  }

*Example Append Metadata Request: JSON*

.. code-block:: javascript

  POST https://example.org/cyclades/v2/volumes/42/metadata

  {"metadata": {"key_to_append": "value_to_append"}}

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Volume not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

Response body contents::

  metadata: {
    <key>: <value>,
    ...
  }

*Example update volume Response*

.. code-block:: javascript

  {
    "metadata": {
      "key1": "value1",
      "key2": "value2",
      ...
    }
  }

Delete Volume
-------------

.. rubric:: Request

======================== ====== ======== ==========
URI                      Method Cyclades OS/Block Storage
======================== ====== ======== ==========
``/volumes/<volume id>`` DELETE ✔        ✔
======================== ====== ======== ==========

|
============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
============== ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
202 (OK)                    Request succeeded
400 (Bad Request)           Malformed server id
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Volume not found
409 (Build In Progress)     Volume is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   Action not supported or service currently
\                           unavailable
=========================== =====================

Reassign Volume
---------------

Reassign the volume to a (different) project (change quota limits)

=============================== ====== ======== ==========
URI                             Method Cyclades OS/Block Storage
=============================== ====== ======== ==========
``/volumes/<volume id>/action`` POST   ✔        ✔
=============================== ====== ======== ==========

|
============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
============== ========================= ======== ==========

.. rubric:: Request

Request body contents::

  reassign: {project: <project id>}

*Example reassign volume Request*

.. code-block:: javascript

  POST https://example.org//cyclades/v2/volumes/42/action

  {"reassign": {"project": "4321"}}


.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Volume not found
409 (Build In Progress)     Volume is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================


List Snapshots
--------------

List all snapshots related to the user.

.. rubric:: Request

====================== ====== ======== ==========
URI                    Method Cyclades OS/Block Storage
====================== ====== ======== ==========
``/snapshots``         GET    ✔        ✔
``/snapshots/detail``  GET    ✔        ✔
====================== ====== ======== ==========

* Both requests return a list of snapshots. The first returns just ``id``,
  ``display_name`` and ``links``, while the second returns the
  `full collection <#snapshot-ref>`_ of snapshot attributes

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Block Storage
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
401 (Unauthorized)          Missing or expired user token
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================

|

Response body contents::

  snapshots: [
    {
      <snapshot attribute>: <value>,
      ...
    }, ...
  ]

The snapshot attributes are listed `here <#snapshot-ref>`_

*Example List Snapshots: JSON (regular)*

.. code-block:: javascript

  GET https://example.org/cyclades/v2/snapshots

  {
    "snapshots": [
      {
        "links": [
          {
            "href": "https://example.org/cyclades/v2/snapshots/42",
            "rel": "self"
          }, {
            "href": "https://example.org/cyclades/v2/snapshots/42",
            "rel": "bookmark"
          }
        ],
        "id": "42",
        "display_name": "Snapshot One",
        "status": "AVAILABLE",
        "size": 2,
        "display_description": null,
        "created_at": "2014-05-19T19:52:04.949734",
        "metadata": {},
        "volume_id": "123",
        "os-extended-snapshot-attribute:progress": "100%"
      }, {
        "links": [
          {
            "href": "https://example.org/cyclades/v2/snapshots/43",
            "rel": "self"
          }, {
            "href": "https://example.org/cyclades/v2/snapshots/43",
            "rel": "bookmark"
          }
        ],
        "id": "43",
        "display_name": "Snapshot Two",
        "status": "AVAILABLE",
        "size": 3,
        "display_description": null,
        "created_at": "2014-05-20T19:52:04.949734",
        "metadata": {},
        "volume_id": "124",
        "os-extended-snapshot-attribute:progress": "100%"
      }
    ]
  }

*Example List Snapshots: JSON (detail)*

.. code-block:: javascript

  GET https://example.org/cyclades/v2/snapshots/detail

  {
    "snapshots": [
      {
        "links": [
          {
            "href": "https://example.org/cyclades/v2/snapshots/42",
            "rel": "self"
          }, {
            "href": "https://example.org/cyclades/v2/snapshots/42",
            "rel": "bookmark"
          }
        ],
        "id": "42",
        "display_name": "Snapshot One",
        "status": "AVAILABLE",
        "size": 2,
        "display_description": null,
        "created_at": "2014-05-19T19:52:04.949734",
        "metadata": {},
        "volume_id": "123",
        "os-extended-snapshot-attribute:progress": "100%"
      }, {
        "links": [
          {
            "href": "https://example.org/cyclades/v2/snapshots/43",
            "rel": "self"
          }, {
            "href": "https://example.org/cyclades/v2/snapshots/43",
            "rel": "bookmark"
          }
        ],
        "id": "43",
        "display_name": "Snapshot Two",
        "status": "AVAILABLE",
        "size": 3,
        "display_description": null,
        "created_at": "2014-05-20T19:52:04.949734",
        "metadata": {},
        "volume_id": "124",
        "os-extended-snapshot-attribute:progress": "100%"
      }
    ]
  }

Get Snapshot Details
--------------------

This operation returns detailed information for a snapshot

.. rubric:: Request

============================ ====== ======== ==========
URI                          Method Cyclades OS/Block Storage
============================ ====== ======== ==========
``/snapshots/<snapshot id>`` GET    ✔        ✔
============================ ====== ======== ==========

|

============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
============== ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed volume id
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Snapshot not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

|

Response body contents::

  snapshot: {
    <snapshot attribute>: <value>,
    ...
  }

Snapshot attributes are explained `here <#snapshot-ref>`_

*Example Get Snapshot Response*

.. code-block:: javascript

  GET https://example.org/cyclades/v2/snapshots/sn4p5h071

  {
    "snapshot": {
      "links": [
        {
          "href": "https://example.org/cyclades/v2/snapshots/42",
          "rel": "self"
        }, {
          "href": "https://example.org/cyclades/v2/snapshots/42",
          "rel": "bookmark"
        }
      ],
      "id": "42",
      "display_name": "Snapshot One",
      "status": "AVAILABLE",
      "size": 2,
      "display_description": null,
      "created_at": "2014-05-19T19:52:04.949734",
      "metadata": {},
      "volume_id": "123",
      "os-extended-snapshot-attribute:progress": "100%",
    }
  }

Create Snapshot
---------------

Create a new snapshot

.. rubric:: Request

============== ====== ======== ==========
URI            Method Cyclades OS/Block Storage
============== ====== ======== ==========
``/snapshots`` POST   ✔        ✔
============== ====== ======== ==========

|
============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
Content-Type   Type or request body      required required
Content-Length Length of request body    required required
============== ========================= ======== ==========

Request body contents::

  snapshot: {
      <snapshot attribute>: <value>,
      ...
  }

=================== ================================ ======== ================
Volume Attribute    Value                            Cyclades OS/Block Storage
=================== ================================ ======== ================
volume_id           Volume to create snapshot from   required required
display_name        The name                         ✔        ✔
display_description A description                    ✔        ✔
force               Whether to snapshot              **✘**    ✔
=================== ================================ ======== ================

*Example Create Volume Request: JSON*

.. code-block:: javascript

  POST https://example.org/cyclades/v2/volumes

  {
    "volume": {
      "volume_id": "44",
      "display_name": "Snapshot Three"
    }
  }

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
202 (OK)                    Request succeeded
400 (Bad Request)           Malformed request data
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Snapshot not found
413 (Over Limit)            Exceeded some resource limit
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

|

Response body contents::

  snapshot: {
    <snapshot attribute>: <value>,
    ...
  }

Snapshots attributes are `listed here <#snapshot-ref>`_.

*Example Create Snapshot Response: JSON*

.. code-block:: javascript

  {
    "snapshot": {
      "links": [
        {
          "href": "https://example.org/cyclades/v2/snapshots/44",
          "rel": "self"
        }, {
          "href": "https://example.org/cyclades/v2/snapshots/44",
          "rel": "bookmark"
        }
      ],
      "id": "44",
      "display_name": "Snapshot Three",
      "status": "CREATING",
      "size": 10,
      "display_description": null,
      "created_at": "2014-05-19T19:52:04.949734",
      "metadata": {},
      "volume_id": "123",
      "os-extended-snapshot-attribute:progress": "100%",
    }
  }

Update Snapshot
---------------

.. rubric:: Response

============================ ====== ======== ==========
URI                          Method Cyclades OS/Block Storage
============================ ====== ======== ==========
``/snapshots/<snapshot id>`` PUT    ✔        ✔
============================ ====== ======== ==========

|
============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
Content-Type   Type or request body      required required
Content-Length Length of request body    required required
============== ========================= ======== ==========

Request body contents::

  snapshot: {
    <snapshot attribute>: <value>,
    ...
  }

=================== ===================== ======== ==========
Attribute           Description           Cyclades OS/Block Storage
=================== ===================== ======== ==========
display_name        Server name           ✔        ✔
display_description Descrition            ✔        ✔
=================== ===================== ======== ==========

*Example Rename Server Request: JSON*

.. code-block:: javascript

  POST https://example.org/cyclades/v2/snapshots/44

  {"snapshot": {"display_name": "New name"}}

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Snapshot not found
409 (Build In Progress)     Snapshot is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

Response body contents::

  snapshot: {
    <snapshot attribute>: <value>,
    ...
  }

Snapshot attributes are explained `here <#snapshot-ref>`_

*Example update snapshot Response*

.. code-block:: javascript

  {
    "snapshot": {
      "id": "44",
      "display_name": "New Name",
      ...
    }
  }

Delete Snapshot
---------------

.. rubric:: Request

============================ ====== ======== ==========
URI                          Method Cyclades OS/Block Storage
============================ ====== ======== ==========
``/snapshots/<snapshot id>`` DELETE ✔        ✔
============================ ====== ======== ==========

|
============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
============== ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
202 (OK)                    Request succeeded
400 (Bad Request)           Malformed server id
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Snapshot not found
409 (Build In Progress)     Snapshot is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   Action not supported or service currently
\                           unavailable
=========================== =====================


List Volume Types
-----------------

.. rubric:: Request

========== ====== ======== ==========
URI        Method Cyclades OS/Block Storage
========== ====== ======== ==========
``/types`` GET    ✔        ✔
========== ====== ======== ==========

|
============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
============== ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
401 (Unauthorized)          Missing or expired user token
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================

|

Response body contents::

  volume_types: [
    {
      <volume type attribute>: <value>,
      ...
    }, ...
  ]

The volume type attributes are listed `here <#volume-type-ref>`_

*Example List Volumes: JSON (regular)*

.. code-block:: javascript

  GET https://example.org/cyclades/v2/types

  {
    "volumes": [
      {
        "id": 1,
        "display_name": "Basic type",
        "extra_specs": {...}
      }, {
        "id": 2,
        "display_name": "Special type",
        "extra_specs": {...}
      }
    ]
  }

Get Volume Type Details
-----------------------

This operation returns detailed information for a volume type

.. rubric:: Request

=========================== ====== ======== ==========
URI                         Method Cyclades OS/Block Storage
=========================== ====== ======== ==========
``/types/<volume type id>`` GET    ✔        ✔
=========================== ====== ======== ==========

|

============== ========================= ======== ==========
Request Header Value                     Cyclades OS/Block Storage
============== ========================= ======== ==========
X-Auth-Token   User authentication token required required
============== ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed volume type id
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Volume type not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

|

Response body contents::

  volume_type: {
    <volume type attribute>: <value>,
    ...
  }

Volume attributes are explained `here <#volume-type-ref>`_

*Example Get Volume Response*

.. code-block:: javascript

  GET https://example.org/cyclades/v2/types/1

  {
    "volume_type": {
      "id": 1,
      "display_name": "Volume Three",
      "extra_specs": {...}
    }
  }


Index of Attributes
-------------------

.. _volume-ref:

Volume Attributes
.................

===================== ======== ================
Volume attribute      Cyclades OS/Block Storage
===================== ======== ================
id                    ✔        ✔
display_name          ✔        ✔
links                 ✔        ✔
status                ✔        ✔
size                  ✔        ✔
display_description   ✔        ✔
created_at            ✔        ✔
metadata              ✔        ✔
snapshot_id           ✔        ✔
source_volid          ✔        ✔
attachments           ✔        ✔
volume_type           ✔        ✔
delete_on_termination ✔        ✔
image_id              ✔        **✘**
project               ✔        **✘**
availability_zone     **✘**    ✔
bootable              **✘**    ✔
===================== ======== ================

* **id** The unique volume ID

* **display_name** A name for the volume

* **links** The reference links for the volume

* **status** The volume status can be CREATING, AVAILABLE or DELETED

* **size** The size of the volume in GB

* **display_description** A description of the volume

* **created_at** Date and time of volumes' creation

* **metadata** A list of key-value metadata pairs

* **snapshot_id** The ID of the snapshot this volume was created from

* **source_volid** The ID of the source volume, this volume was created from

* **attachments** One or more instance attachments

* **volume_type** The type of the volume (See Volume types API)

* **delete_on_termination** Whether this volume will be deleted on termination

* **image_id** The ID of the image this volume was created from

* **project** The ID of the project this volume is assigned to (quotas)

.. _snapshot-ref:

Snapshot Attributes
...................

========================================= ======== ================
Snapshot attribute                        Cyclades OS/Block Storage
========================================= ======== ================
id                                        ✔        ✔
display_name                              ✔        ✔
links                                     ✔        ✔
display_description                       ✔        ✔
status                                    ✔        ✔
created_at                                ✔        ✔
size                                      ✔        ✔
volume_id                                 ✔        ✔
metadata                                  ✔        ✔
os-extended-snapshot-attribute:progress   ✔        ✔
os-extended-snapshot-attribute:project_id **✘**    ✔
========================================= ======== ================

* **id** The unique snapshot ID

* **display_name** A name for the snapshot

* **links** The reference links for the snapshot

* **status** The snapshot status can be CREATING, AVAILABLE or DELETED

* **size** The size of the snapshot in GB

* **display_description** A description of the snapshot

* **created_at** Date and time of snapshots' creation

* **volume_id** The volume this is a snapshot of

* **metadata** A list of key-value metadata pairs

* **os-extended-snapshot-attribute:progress** creation progress

.. _volume-type-ref:

Volume Type Attributes
......................

================== ======== ================
Snapshot attribute Cyclades OS/Block Storage
================== ======== ================
id                 ✔        ✔
display_name       ✔        ✔
extra_specs        ✔        ✔
================== ======== ================

* **id** The ID of the volume type

* **display_name** A name for the volume type

* **extra_specs** A dictionary of various specifications

