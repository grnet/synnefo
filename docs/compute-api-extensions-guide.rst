.. _compute-api-extensions-guide:

API Guide
*********

The Cyclades/Compute API Extensions contain some additions to the core
Cyclades/Compute API. In order to be compatible with the OpenStack API, these
additions are mapped to the `OpenStack Compute API v2 Extensions
<http://developer.openstack.org/api-ref-compute-v2-ext.html>`_.

You are advised to consult the "Overview" and "General API Information"
sections of the :ref:`Compute API guide <compute-api-guide>`, which have some
important information for topics such as authentication, fault handling, etc.

API Operations
==============

.. rubric:: Volume attachments

========================== ============================================================== ====== ======== ==========
Description                URI                                                            Method Cyclades OS/Compute
========================== ============================================================== ====== ======== ==========
`List <#list-volumes>`_    ``/servers/{server_id}/os-volume_attachments``                 GET    ✔        ✔
`Attach <#attach-volume>`_ ``/servers/{server_id}/os-volume_attachments``                 POST   ✔        ✔
`Show <#show-volume>`_     ``/servers/{server_id}/os-volume_attachments/{attachment_id}`` GET    ✔        ✔
`Detach <#detach-volume>`_ ``/servers/{server_id}/os-volume_attachments/{attachment_id}`` DELETE ✔        ✔
========================== ============================================================== ====== ======== ==========

List Volumes
------------

List all volume attachments of a server.

.. rubric:: Request

============================================== ====== ======== ==========
URI                                            Method Cyclades OS/Compute
============================================== ====== ======== ==========
``/servers/{server_id}/os-volume_attachments`` GET    ✔        ✔
============================================== ====== ======== ==========

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

================= =================================== ======== ==========
Request Parameter Value                               Cyclades OS/Compute
================= =================================== ======== ==========
json              Respond in json                     default  **✘**
xml               Respond in xml                      ✔        **✘**
================= =================================== ======== ==========

* **json** and **xml** parameters are mutually exclusive. If none supported,
  the response will be formated in json.

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Invalid or malformed ``changes-since`` parameter
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

|

Response body contents::

    {
      "volumeAttachments": [
        {
            "volume_attachment_attribute": <value>,
            ...
        }, ...
      ]
    }

The volume attachment attributes are listed `here <#volume-attachment-ref>`_.


*Example List Volumes: JSON (regular)*

.. code-block:: javascript

  GET https://example.org/compute/v2.0/servers/1134/os-volume_attachments

  {
    "volumeAttachments": [
      {
        "device": "",      # Unused
        "serverId": 1134,
        "id": 9,
        "volumeId": 9
      }, {
        "device": "",      # Unused
        "serverId": 1134,
        "id": 99,
        "volumeId": 99
      }
    ]
  }


Attach Volume
-------------

Attach a volume to a server.

.. rubric:: Request

============================================== ====== ======== ==========
URI                                            Method Cyclades OS/Compute
============================================== ====== ======== ==========
``/servers/{server_id}/os-volume_attachments`` POST    ✔        ✔
============================================== ====== ======== ==========

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

|

================= ===============
Request Parameter Value
================= ===============
json              Respond in json
xml               Respond in xml
================= ===============

Request body contents::

  {
    "volumeAttachment": {
        "volumeId": <value>,
    }
  }

=========== ==================== ======== ==========
Attributes  Description          Cyclades OS/Compute
=========== ==================== ======== ==========
volumeId    The volume id        ✔        ✔
=========== ==================== ======== ==========

* **volumeId** is the id of the volume to be attached

*Example Attach Volume Request: JSON*

.. code-block:: javascript

  {
    "volumeAttachment": {
        "volumeId": 9,
    }
  }


.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request data
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Server or Volume not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

Response body contents::

  {
    "volumeAttachment": {
        "volume_attachment_attribute": <value>,
        ...
    }
  }

The volume attachment attributes are listed `here <#volume-attachment-ref>`_.


*Example Attach Volume Response: JSON*

.. code-block:: javascript

  POST https://example.org/compute/v2.0/servers/1134/os-volume_attachments

  {
    "volumeAttachment": {
        "device": "",      # Unused
        "serverId": 1134,
        "id": 9,
        "volumeId": 9
    }
  }


Show Volume
-----------

Show information for a volume that is attached to a server.

.. rubric:: Request

============================================================== ====== ======== ==========
URI                                                            Method Cyclades OS/Compute
============================================================== ====== ======== ==========
``/servers/{server_id}/os-volume_attachments/{attachment_id}`` GET    ✔        ✔
============================================================== ====== ======== ==========

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

|

================= ===============
Request Parameter Value
================= ===============
json              Respond in json
xml               Respond in xml
================= ===============


.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request data
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Server or Volume not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

|

Response body contents::

  {
    "volumeAttachment": {
        "volume_attachment_attribute": <value>,
        ...
    }
  }

The volume attachment attributes are listed `here <#volume-attachment-ref>`_.


*Example Show Volume Response: JSON*

.. code-block:: javascript

  POST https://example.org/compute/v2.0/servers/1134/os-volume_attachments/9

  {
    "volumeAttachment": {
        "device": "",      # Unused
        "serverId": 1134,
        "id": 9,
        "volumeId": 9
    }
  }


Detach Volume
-------------

Detach a volume from a server.

.. rubric:: Request

============================================================== ====== ======== ==========
URI                                                            Method Cyclades OS/Compute
============================================================== ====== ======== ==========
``/servers/{server_id}/os-volume_attachments/{attachment_id}`` DELETE    ✔        ✔
============================================================== ====== ======== ==========

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

|

================= ===============
Request Parameter Value
================= ===============
json              Respond in json
xml               Respond in xml
================= ===============

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request data
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Server or Volume not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================


Index of Attributes
-------------------

.. _volume-attachment-ref:

Volume Attachment Attributes
............................

=================== ======== ==========
Volume attribute    Cyclades OS/Compute
=================== ======== ==========
device              **✘**    ✔
id                  ✔        ✔
serverId            ✔        ✔
volumeId            ✔        ✔
=================== ======== ==========

* **device** is unused in our case

* **id**, **volumeId** refer to the id of the volume

* **serverId** is the ID of the server where the volume is attached
