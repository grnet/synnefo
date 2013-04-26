.. _cyclades-api-guide:

API Guide
*********

`Cyclades <cyclades.html>`_ is the compute service developed by `GRNET 
<http://www.grnet.gr>`_ as part of the `synnefo <http://www.synnefo.org>`_
software. Cyclades API started as an extension of the `OpenStack Compute API v2
<http://docs.openstack.org/api/openstack-compute/2/content>`_.

This document's goals are:

* Define the Cyclades/Compute ReST API
* Clarify the differences between Cyclades and OS/Compute

Users and developers who wish to access a Synnefo Cyclades deployment through
its ReST API are advised to use the `kamaki <http://docs.dev.grnet.gr/kamaki>`_
command-line client and associated python library, instead of making direct
calls.

Overview
========

* It is not defined if requests for invalid URLs should return 404 or a Fault.
  We return a BadRequest Fault.
* It is not defined if requests with a wrong HTTP method should return 405 or a
  Fault. We return a BadRequest Fault.


General API Information
=======================

Authentication
--------------

All requests use the same authentication method: an ``X-Auth-Token`` header is
passed to the servive, which is used to authenticate the user and retrieve user
related information. No other user details are passed through HTTP.

Efficient Polling with the Changes-Since Parameter
--------------------------------------------------

* Effectively limit support of the changes-since parameter in **List Servers**
  and **List Images**.

* Assume that garbage collection of deleted servers will only affect servers
  deleted ``POLL_TIME`` seconds (default: 3600) in the past or earlier. Else
  loose the information of a server getting deleted.

* Images do not support a deleted state, so deletions cannot be tracked.

Limitations
-----------

* Version MIME type and vesionless requests are not currently supported.

* Cyclades only supports JSON Requests and JSON/XML Responses. XML Requests are
  currently not supported.

* Optional content compression support is currently not supported.

* To prevent abuse, HTTP sessions have a timeout of 20 seconds before being
  closed.

* Full URI references and ``self`` and ``bookmark`` links are not supported.

* Pagination is currently not supported.

* Cached responses are currently not supported.

* Limits are currently not supported.

* Extensions are currently not supported.


API Operations
==============

Servers
-------

List Servers
............

List all virtual servers owned by the user.

.. rubric:: Request

=================== ====== ======== ==========
URI                 Method Cyclades OS/Compute
=================== ====== ======== ==========
``/servers``        GET    ✔        ✔
``/servers/detail`` GET    ✔        ✔
=================== ====== ======== ==========

* Both requests return a list of servers. The first returns just ``id`` and
  ``name``, while the second returns the full collections of server
  attributes.

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
changes-since     Servers delete since that timestamp ✔        ✔
image             Image reference                     **✘**    ✔
flavor            VM flavor reference                 **✘**    ✔
server            Server flavor reference             **✘**    ✔
status            Server status                       **✘**    ✔
marker            Last list last ID                   **✘**    ✔
limit             Page size                           **✘**    ✔
================= =================================== ======== ==========

* **json** and **xml** parameters are mutually exclusive. If none supported,
the response will be formated in json.

* **status** refers to the `server status <#status-ref>`_

* **changes-since** must be an ISO8601 date string

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
304 (No servers since date) Can be returned if ``changes-since`` is given
400 (Bad Request)           Invalid or malformed ``changes-since`` parameter
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

|

Response body contents::

  servers: [
    {
      <server attribute>: <value>,
      ...
    }, ...
  ]

================= ====================== ======== ==========
Server Attributes Description            Cyclades OS/Compute
================= ====================== ======== ==========
id                The server id          ✔        ✔
name              The server name        ✔        ✔
hostId            Server playground      empty    ✔
created           Creation date          ✔        ✔
updated           Creation date          ✔        ✔
flavorRef         The flavor id          ✔        **✘**
flavor            The flavor id          **✘**    ✔
imageRef          The image id           ✔        **✘**
image             The image id           **✘**    ✔
progress          Build progress         ✔        ✔
status            Server status          ✔        ✔
attachments       Network interfaces     ✔        **✘**
addresses         Network interfaces     **✘**    ✔
metadata          Server custom metadata ✔        ✔
================= ====================== ======== ==========

* **hostId** is not used in Cyclades, but is returned as an empty string for
  compatibility

* **progress** is changing while the server is building up and has values
  between 0 and 100. When it reaches 100 the server is built.

* **status** refers to `the status <#status-ref>`_ of the server

* **metadata** are custom key:value pairs used to specify various attributes of
  the VM (e.g. OS, super user, etc.)

* **attachments** in Cyclades are lists of network interfaces (nics).
  **Attachments** are different to OS/Compute's **addresses**. The former is a
  list of the server's `network interface connections <#nic-ref>`_ while the
  later is just a list of networks. Thus, a Cyclades virtual server may be
  connected to the same network through more than one distinct network
  interfaces (e.g. server 43 is connected to network 101 with nic-43-1 and
  nic-43-2 in the example bellow).

* **Network Interfaces (NICs)** contain information about a server's connection
  to a network. Each NIC is identified by an id of the form
  nic-<server-id>-<ordinal-number>. More details can be found `here
  <#nic-ref>`_.

**Example List Servers: JSON**

.. code-block:: javascript

  {
    "servers":
      {"values": [
        {
          "attachments": {
            "values": [
              {
                "id": "nic-42-0",
                "network_id": "101",
                "mac_address": "aa:00:00:49:2e:7e",
                "firewallProfile": "DISABLED",
                "ipv4": "192.168.4.5",
                "ipv6": "2001:648:2ffc:1222:a800:ff:fef5:3f5b"
              }
            ]
          },
          "created': '2011-04-19T10:18:52.085737+00:00',
          "flavorRef": "1",
          "hostId": "",
          "id": "42",
          "imageRef": "3",
          "metadata": {"values": {"foo": "bar"}},
          "name": "My Server",
          "status": "ACTIVE",
          "updated": "2011-05-29T14:07:07.037602+00:00"
        }, {
          "attachments": {
            "values": [
              {
                "id": "nic-43-0",
                "mac_address": "aa:00:00:91:2f:df",
                "network_id": "1",
                "ipv4": "192.168.32.2"
              }, {
                "id": "nic-43-1",
                "network_id": "101",
                "mac_address": "aa:00:00:49:2g:7f",
                "firewallProfile": "DISABLED",
                "ipv4": "192.168.32.6",
                "ipv6": "2001:648:2ffc:1222:a800:ff:fef5:3f5c'
              }, {
                "id": "nic-43-2",
                "network_id": "101",
                "mac_address": "aa:00:00:51:2h:7f",
                "firewallProfile": "DISABLED",
                "ipv4": "192.168.32.7",
                "ipv6": "2001:638:2eec:1222:a800:ff:fef5:3f5c"
              }
            ]
          },
          "created": "2011-05-02T20:51:08.527759+00:00",
          "flavorRef": "1",
          "hostId": "",
          "id": "43",
          "imageRef": "3",
          "name": "Other Server",
          "description": "A sample server to showcase server requests",
          "progress": "0",
          "status": "ACTIVE",
          "updated": "2011-05-29T14:59:11.267087+00:00"
        }
      ]
    }
  }


Create Server
.............

Create a new virtual server

.. rubric:: Request

============ ====== ======== ==========
URI          Method Cyclades OS/Compute
============ ====== ======== ==========
``/servers`` POST   ✔        ✔
============ ====== ======== ==========

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

================= ===============
Request Parameter Value          
================= ===============
json              Respond in json
xml               Respond in xml 
================= ===============

Request body contents::

  server: {
      <server attribute>: <value>,
      ...
      personality: [
        {
          <personality attribute>: <value>,
          ...
        },
        ...
      ],
      ...
  }

=========== ==================== ======== ==========
Attributes  Description          Cyclades OS/Compute
=========== ==================== ======== ==========
name        The server name      ✔        ✔
imageRef    Image id             ✔        ✔
flavorRef   Resources flavor     ✔        ✔
personality Personality contents ✔        ✔
metadata    Custom metadata      ✔        ✔
=========== ==================== ======== ==========

* **name** can be any string

* **imageRed** and **flavorRed** should refer to existing images and hardware
  flavors accessible by the user

* **metadata** are ``key``:``value`` pairs of custom server-specific metadata.
  There are no semantic limitations.

* **personality** (optional) is a list of personality injections. A personality
  injection is a small set of changes to a virtual server. Each change modifies
  a file on the virtual server, by injecting some data in it. The injected data
  (``contents``) should exceed 10240 *bytes* in size and must be base64
  encoded.A personality injection contains the following attributes:

====================== =================== ======== ==========
Personality Attributes Description         Cyclades OS/Compute
====================== =================== ======== ==========
path                   File path on server ✔        ✔
contents               Data to inject      ✔        ✔
group                  User group          ✔        **✘**
mode                   File access mode    ✔        **✘**
owner                  File owner          ✔        **✘**
====================== =================== ======== ==========

|

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request data
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Image or Flavor not found
413 (Over Limit)            Exceeded some resource limit (#VMs, personality
size, etc.) 
415 (Bad Media Type)        
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

|

Response body contents::

  server: {
    <server attribute>: <value>,
    ...
  }

Server attributes are `listed here <#server-ref>`_.

**Example Create Server Response: JSON**

.. code-block:: javascript

  {
    "server": {
      "id": 28130
      "status": "BUILD",
      "updated": "2013-04-10T13:52:18.140686+00:00",
      "hostId": "",
      "name": "My Server Name: Example Name",
      "imageRef": "da7a211f-...-f901ce81a3e6",
      "created": "2013-04-10T13:52:17.085402+00:00",
      "flavorRef": 289,
      "adminPass": "fKCqlZe2at",
      "suspended": false,
      "progress": 0
    }
  }

**Example Create Server Response: XML**:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <server xmlns="http://docs.openstack.org/compute/api/v1.1"\
    xmlns:atom="http://www.w3.org/2005/Atom"
    id="1"
    status="BUILD"
    hostId="",
    name="My Server Name: Example Name"
    imageRef="da7a211f-...-f901ce81a3e6"
    created="2013-04-10T13:52:17.085402+00:00"
    flavorRef="289"
    adminPass="fKCqlZe2at"
    suspended="false"
    progress="0"
  />

Get Server Stats
................

.. note:: This operation is not part of OS/Compute v2.

This operation returns URLs of graphs showing CPU and Network statistics.

.. rubric:: Request

============================== ====== ======== ==========
URI                            Method Cyclades OS/Compute
============================== ====== ======== ==========
``/servers/<server-id>/stats`` GET    ✔        **✘**
============================== ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

================= ===============
Request Parameter Value          
================= ===============
json              Respond in json
xml               Respond in xml 
================= ===============

* **json** and **xml** parameters are mutually exclusive. If none supported,
the response will be formated in json.

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Invalid server ID or Server deleted
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Server not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

|

Response body contents::

  stats: {<parameter>: <value> }

============= ======================
Parameter     Description           
============= ======================
serverRef     Server ID
refresh       Refresh frequency
cpuBar        Latest CPU load graph URL
cpuTimeSeries CPU load / time graph URL
netBar        Latest Network load graph URL
netTimeSeries Network load / time graph URL
============= ======================

* **refresh** is the recommended sampling rate

**Example Get Server Stats Response: JSON**:

.. code-block:: javascript

  {
    "stats": {
      "serverRef": 1,
      "refresh": 60,
      "cpuBar": "http://stats.okeanos.grnet.gr/b9a...048c/cpu-bar.png",
      "cpuTimeSeries": "http://stats.okeanos.grnet.gr/b9a...048c/cpu-ts.png",
      "netBar": "http://stats.okeanos.grnet.gr/b9a...048c/net-bar.png",
      "netTimeSeries": "http://stats.okeanos.grnet.gr/b9a...048c/net-ts.png"
    }
  }

**Example Get Network Details Response: XML**:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <stats xmlns="http://docs.openstack.org/compute/api/v1.1"\
    xmlns:atom="http://www.w3.org/2005/Atom"
    serverRef="1"
    refresh="60"
    cpuBar="https://www.example.com/stats/snf-42/cpu-bar/",
    netTimeSeries="https://example.com/stats/snf-42/net-ts/",
    netBar="https://example.com/stats/snf-42/net-bar/",
    cpuTimeSeries="https://www.example.com/stats/snf-42/cpu-ts/"
  </stats>

Get Server Diagnostics
......................

.. note:: This operation is not part of OS/Compute v2.

This operation returns diagnostic information (logs) for a server.

.. rubric:: Request

==================================== ====== ======== ==========
URI                                  Method Cyclades OS/Compute
==================================== ====== ======== ==========
``/servers/<server-id>/diagnostics`` GET    ✔        **✘**
==================================== ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

============================== ====== ======== ==========
URI                            Method Cyclades OS/Compute
============================== ====== ======== ==========
``/servers/<server-id>/stats`` GET    ✔        **✘**
============================== ====== ======== ==========

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Invalid server ID or Server deleted
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Server not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

|

Response body contents::

  [
    {
      <diagnostic attribute}: <value>,
      ...
    }, {
      <diagnostic attribute}: <value>,
      ...
    },
    ...
  ]

==================== ===========
Diagnostic attribute Description
==================== ===========
level                Debug level
created              Log entry timestamp
source               Log source proccess
source_date          Log source date          
message              Log description
details              Detailed log description
==================== ===========

For example:

.. code-block:: javascript

  [
    {
      "level": "DEBUG",
      "created": "2013-04-09T15:25:53.965144+00:00",
      "source": "image-helper-task-start",
      "source_date": "2013-04-09T15:25:53.954695+00:00",
      "message": "FixPartitionTable",
      "details": null
    }, {
      "level": "DEBUG",
      "created": "2013-04-09T15:25:46.413718+00:00",
      "source": "image-info",
      "source_date": "2013-04-09T15:25:46.404477+00:00",
      "message": "Starting customization VM...",
      "details": null
    }, {
      "level": "DEBUG",
      "created": "2013-04-09T15:25:46.207038+00:00",
      "source": "image-info",
      "source_date": "2013-04-09T15:25:46.197183+00:00",
      "message": "Image copy finished.",
      "details": "All operations finished as they should. No errors reported."
    }
  ]

Get Server Details
..................

This operation returns detailed information for a virtual server

.. rubric:: Request

======================== ====== ======== ==========
URI                      Method Cyclades OS/Compute
======================== ====== ======== ==========
``/servers/<server id>`` GET    ✔        ✔
======================== ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed server id
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Server not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

|

Response body contents::

  server: {
    <server attribute>: <value>,
    ...
  }

================= ====================== ======== ==========
Server Attributes Description            Cyclades OS/Compute
================= ====================== ======== ==========
id                The server id          ✔        ✔
name              The server name        ✔        ✔
hostId            Server playground      empty    ✔
created           Creation date          ✔        ✔
updated           Creation date          ✔        ✔
flavorRef         The flavor id          ✔        **✘**
flavor            The flavor id          **✘**    ✔
imageRef          The image id           ✔        **✘**
image             The image id           **✘**    ✔
progress          Build progress         ✔        ✔
status            Server status          ✔        ✔
suspended         If server is suspended ✔        **✘**
attachments       Network interfaces     ✔        **✘**
addresses         Network interfaces     **✘**    ✔
metadata          Server custom metadata ✔        ✔
diagnostics       Diagnostic information ✔        **✘**
================= ====================== ======== ==========

* **hostId** is not used in Cyclades, but is returned as an empty string for
  compatibility

* **progress** is changing while the server is building up and has values
  between 0 and 100. When it reaches 100 the server is built.

* **status** refers to `the status <#status-ref>`_ of the server

* **metadata** are custom key:value pairs used to specify various attributes of
  the VM (e.g. OS, super user, etc.)

* **attachments** in Cyclades are lists of network interfaces (NICs).
  **Attachments** are different to OS/Compute's **addresses**. The former is a
  list of the server's `network interface connections <#nic-ref>`_ while the
  later is just a list of networks. Thus, a Cyclades virtual server may be
  connected to the same network through more than one distinct network
  interfaces.

* **diagnostics** is a list of items that contain key:value information useful
  for diagnosing the server behavior and may be used by the administrators of
  deployed Synnefo setups.

**Example Details for server with id 42042, in JSON**

.. code-block:: javascript

  {
    "server": {
      "id": 42042,
      "name": "My Example Server",
      "status": "ACTIVE",
      "updated": "2013-04-18T10:09:57.824266+00:00",
      "hostId": "",
      "imageRef": "926a1bc5-2d85-49d4-aebe-0fc127ed89b9",
      "created": "2013-04-18T10:06:58.288273+00:00",
      "flavorRef": 22,
      "attachments": {
        "values": [{
          "network_id": "1888",
          "mac_address": "aa:0c:f5:ad:16:41",
          "firewallProfile": "DISABLED",
          "ipv4": "83.212.112.56",
          "ipv6": "2001:648:2ffc:1119:a80c:f5ff:fead:1641",
          "id": "nic-42042-0"
        }]
      },
      "suspended": false,
      "diagnostics": [{
        "level": "DEBUG",
        "created": "2013-04-18T10:09:52.776920+00:00",
        "source": "image-info",
        "source_date": "2013-04-18T10:09:52.709791+00:00",
        "message": "Image customization finished successfully.",
        "details": null
      }],
      "progress": 100,
      "metadata": {
        "values": {"OS": "windows", "users": "Administrator"}
      }
    }
  }

.. note:: the ``values`` layer is not featured in OS/Compute API

Rename Server
.............

Modify the ``name`` attribute of a virtual server. OS/Compute API also features
the modification of IP addresses

.. rubric:: Response

======================== ====== ======== ==========
URI                      Method Cyclades OS/Compute
======================== ====== ======== ==========
``/servers/<server id>`` PUT    ✔        ✔
======================== ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

Request body contents::

  server: {
    <server attribute>: <value>,
    ...
  }

=========== ==================== ======== ==========
Attribute   Description          Cyclades OS/Compute
=========== ==================== ======== ==========
name        The server name      ✔        ✔
accessIPv4  IP v4 address        **✘**    ✔
accessIPv6  IP v6 address        **✘**    ✔
=========== ==================== ======== ==========

* Cyclades support multiple network connections per virtual server, which
  explains the above differences in request body attributes.

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or malformed server id
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Server not found
415 (Bad Media Type)
409 (Build In Progress)     Server is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

.. note:: In case of a 204 return code, there will be no request results
  according to the Cyclades API. Compute OS API suggests that response should
  include the new server details.

Delete Server
.............

Delete a virtual server. When a server is deleted, all its connections are
deleted as well.

.. rubric:: Request

======================== ====== ======== ==========
URI                      Method Cyclades OS/Compute
======================== ====== ======== ==========
``/servers/<server id>`` DELETE ✔        ✔
======================== ====== ======== ==========

* **server-id** is the identifier of the virtual server.

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Malformed server id or machine already deleted
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Server not found
409 (Build In Progress)     Server is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   Action not supported or service currently
\                           unavailable
=========================== =====================

.. note:: In case of a 204 code, response body should be empty

List Server Addresses
.....................

List all network connections of a server. In Cyclades API, connections are
represented as Network Connection Interfaces (NICs), which describe a server -
network relation through their respective identifiers. This mechanism ensures
flexibility and multiple networks connecting the same virtual servers.

The Synnefo/Cyclades approach in this matter differs substantially to the
`one suggested by the OS/Compute API <http://docs.openstack.org/api/openstack-compute/2/content/List_Addresses-d1e3014.html>`_.

.. rubric:: Request

============================ ====== ======== ==========
URI                          Method Cyclades OS/Compute
============================ ====== ======== ==========
``/servers/<server id>/ips`` GET    ✔        ✔
============================ ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed server id or machine already deleted
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Server not found
409 (Build In Progress)     Server is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   Service currently unavailable
=========================== =====================

Response body contents::

  addresses: {values: [
    {
      <NIC attribute>: <value>,
      ...
    },
    ...
  ]}

A Network Interface Connection (or NIC) connects the current server to a
network, through their respective identifiers. More information in NIC
attributes are `enlisted here <#nic-ref>`_.

**Example List Addresses: JSON**

.. code-block:: javascript

  {
    "addresses": {
      "values": [
        {
          "id": "nic-25455-0"
          "network_id": "1",
          "mac_address": "aa:00:03:7a:84:bb",
          "firewallProfile": "DISABLED",
          "ipv4": "192.168.0.27",
          "ipv6": "2001:646:2ffc:1222:a820:3fd:fe7a:84bb",
        }, {
          "id": "nic-25455-1"
          "network_id": "7",
          "mac_address": "aa:00:03:7a:84:cc",
          "firewallProfile": "DISABLED",
          "ipv4": "192.168.0.28",
          "ipv6": "2002:646:2fec:1222:a820:3fd:fe7a:84bc",
        },
      ]
    }
  }

Get Server NICs by Network
..........................

Return the NIC that connects a server to a network.

The semantics of this operation are substantially different to the respective
OS/Compute
`List Addresses by Network semantics <http://docs.openstack.org/api/openstack-compute/2/content/List_Addresses_by_Network-d1e3118.html>`_.

.. rubric:: Request

========================================= ====== ======== ==========
URI                                       Method Cyclades OS/Compute
========================================= ====== ======== ==========
``/servers/<server id>/ips/<network id>`` GET    ✔        ✔
========================================= ====== ======== ==========

* **server id** is the identifier of the virtual server

* **network id** is the identifier of the network

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed server id or machine already deleted
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Server not found
409 (Build In Progress)     Server is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   Service currently unavailable
=========================== =====================

|

Response body contents::

  network: {
    <NIC attributes>: <value>,
    ...
  }

Network Interface Connection (NIC) attributes are listed `here <#nic-ref>`_. 

**List Server NICs Example with server id 25455, network id 7: JSON**

.. code-block:: javascript

  {
    "network": {
      "id": "nic-25455-0"
      "network_id": "7",
      "mac_address": "aa:00:03:7a:84:bb",
      "firewallProfile": "DISABLED",
      "ipv4": "192.168.0.27",
      "ipv6": "2001:646:2ffc:1222:a820:3fd:fe7a:84bb",
    }
  }


List Server Metadata
....................

List the metadata of a server

.. note:: This operation is semantically equivalent in Cyclades and OS/Compute
  besides the different URI.

.. rubric:: Request

================================= ====== ======== ==========
URI                               Method Cyclades OS/Compute
================================= ====== ======== ==========
``/servers/<server-id>/meta``     GET    ✔        **✘**
``/servers/<server-id>/metadata`` GET    **✘**    ✔
================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Invalid server ID or Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Server not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Response body contents::

  metadata: {values:
    {
      <metadatum key>: <value>,
      ...
    }
  }

**Example List Server Metadata: JSON**

.. code-block:: javascript

  { 
    ""metadata": {
      "values": {
        "OS": "Linux",
        "users": "root"
      }
    }
  }

.. note:: In OS/Compute API  the ``values`` level is missing from the response.

Set / Update Server Metadata
............................

In Cyclades API, setting new metadata and updating the values of existing ones
is achieved with the same type of request (``POST``), while in OS/Compute API
there are two separate request types (``PUT`` and ``POST`` for
`setting new <http://docs.openstack.org/api/openstack-compute/2/content/Create_or_Replace_Metadata-d1e5358.html>`_
and
`updating existing <http://docs.openstack.org/api/openstack-compute/2/content/Update_Metadata-d1e5208.html>`_
metadata, respectively).

In Cyclades API, metadata keys which are not referred by the operation will
remain intact, while metadata referred by the operation will be overwritten.

.. rubric:: Request

================================= ====== ======== ==========
URI                               Method Cyclades OS/Compute
================================= ====== ======== ==========
``/servers/<server-id>/meta``     POST    ✔       **✘**
``/servers/<server-id>/metadata`` PUT    **✘**    ✔
``/servers/<server-id>/metadata`` POST   **✘**    ✔
================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

Request body contents::

  metadata: {
    <metadatum key>: <value>,
    ...
  }

**Example Request Set / Update Server Metadata: JSON**

.. code-block:: javascript

  {"metadata": {"role": "webmail", "users": "root,maild"}}

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Request succeeded
400 (Bad Request)           Invalid server ID or Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Server not found
413 (OverLimit)             Maximum number of metadata exceeded
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Response body contents::

  metadata: {
    <metadatum key>: <value>,
    ...
  }

**Example Response Set / Update Server Metadata: JSON**

.. code-block:: javascript

  {"metadata": {"OS": "Linux", "role": "webmail", "users": "root,maild"}}

Get Server Metadata Item
........................

Get the value of a specific metadatum of a virtual server

.. note:: This operation is semantically equivalent in Cyclades and OS/Compute
  besides the different URI.

.. rubric:: Request

======================================= ====== ======== ==========
URI                                     Method Cyclades OS/Compute
======================================= ====== ======== ==========
``/servers/<server-id>/meta/<key>``     GET    ✔        **✘**
``/servers/<server-id>/metadata/<key>`` GET    **✘**    ✔
======================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server

* **key** is the key of a matadatum ``key``:``value`` pair

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Invalid server ID or Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Metadatum key not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Response body content::

  metadata: {<metadatum key>: <value>}

**Example Get Server Metadatum for Item 'role', JSON**

.. code-block:: javascript

  {"metadata": {"role": "webmail"}}

.. note:: In OS/Compute, ``metadata`` is ``meta``

Set / Update Server Metadatum Item
..................................

Set a new or update an existing a metadum value for a virtual server.

.. note:: This operation is semantically equivalent in Cyclades and OS/Compute
  besides the different URI.

.. rubric:: Request

======================================= ====== ======== ==========
URI                                     Method Cyclades OS/Compute
======================================= ====== ======== ==========
``/servers/<server-id>/meta/<key>``     PUT    ✔        **✘**
``/servers/<server-id>/metadata/<key>`` PUT    **✘**    ✔
======================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server

* **key** is the key of a matadatum ``key``:``value`` pair

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

Request body content::

  meta: {<metadatum key>: <value>}

**Example Request to Set or Update Server Metadatum "role": JSON**

.. code-block:: javascript

  {"meta": {"role": "gateway"}}

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Request succeeded
400 (Bad Request)           Invalid server ID or Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Metadatum key not found
413 (OverLimit)             Maximum number of metadata exceeded
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== ====================

Response body content::

  meta: {<metadatum key>: <value>}

**Example Set or Update Server Metadatum "role":"gateway": JSON**

.. code-block:: javascript

  {"meta": {"role": "gateway"}}

Delete Server Metadatum
.......................

Delete a metadatum of a virtual server

.. note:: This operation is semantically equivalent in Cyclades and OS/Compute
  besides the different URI.

.. rubric:: Request

======================================= ====== ======== ==========
URI                                     Method Cyclades OS/Compute
======================================= ====== ======== ==========
``/servers/<server-id>/meta/<key>``     DELETE ✔        **✘**
``/servers/<server-id>/metadata/<key>`` DELETE **✘**    ✔
======================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server

* **key** is the key of a matadatum ``key``:``value`` pair

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Invalid server ID
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Metadatum key not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

.. note:: In case of a 204 code, response body should be empty

Server Actions
--------------

Actions are operations that are achieved through the same type of request
(``POST``). There are differences in the implementations of some operations
between Synnefo/Cyclades and OS/Compute. Although this document focuses on
Synnefo/Cyclades, differences and similarities between the APIs are also
briefed.

============================= ======== ==========
Operations                    Cyclades OS/Compute
============================= ======== ==========
Start Server                  ✔        **✘**
Shutdown Server               ✔        **✘**
Reboot Server                 ✔        ✔
Get Server Console            ✔        **✘**
Set Firewall Profile          ✔        **✘**
Change Administrator Password **✘**    ✔
Rebuild Server                **✘**    ✔
Resize Server                 **✘**    ✔
Confirm Resized Server        **✘**    ✔
Revert Resized Server         **✘**    ✔
Create Image                  **✘**    ✔
============================= ======== ==========

.. rubric:: Request

=============================== ====== ======== ==========
URI                             Method Cyclades OS/Compute
=============================== ====== ======== ==========
``/servers/<server id>/action`` POST   ✔        ✔
=============================== ====== ======== ==========

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

.. note:: Request body varies between operations (see bellow)

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded (for console operation)
202 (OK)                    Request succeeded
400 (Bad Request)           Invalid request or unknown action
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

.. note:: Response body varies between operations (see bellow)

Start server
................

This operation transitions a server from a STOPPED to an ACTIVE state.

Request body contents::

  start: {}

**Example Start Server: JSON**

.. code-block:: javascript

  {"start": {}}

.. note:: Response body should be empty

Reboot Server
.............

This operation transitions a server from ``ACTIVE`` to ``REBOOT`` and then
``ACTIVE`` again.

Synnefo and OS/Compute APIs offer two reboot modes: ``soft``
and ``hard``. OS/Compute distinguishes between the two intermediate states
(``REBOOT`` and ``HARD_REBOOT``) while rebooting, while Synnefo/Cyclades use
the ``REBOOT`` term only. The expected behavior is the same, though.

Request body contents::

  reboot: {type: <reboot type>}

* **reboot type** can be either ``SOFT`` or ``HARD``.

**Example (soft) Reboot Server: JSON**

.. code-block:: javascript
  
  {"reboot" : { "type": "soft"}}

.. note:: Response body should be empty

Shutdown server
...............

This operation transitions a server from an ACTIVE to a STOPPED state.

Request body contents::

  shutdown: {}

**Example Shutdown Server: JSON**

.. code-block:: javascript

  {"shutdown": {}}

.. note:: Response body should be empty

Get Server Console
..................

.. note:: This operation is not part of OS/Compute API

The console operation arranges for an OOB console of the specified type. Only
consoles of type ``vnc`` are supported for now. Cyclades server uses a running
instance of vncauthproxy to setup proper VNC forwarding with a random password,
then returns the necessary VNC connection info to the caller.

Request body contents::

  console: {type: vnc}

**Example Get Server Console: JSON**

.. code-block:: javascript

  {"console": {"type": "vnc" }

Response body contents::

  console: {
    <vnc attribute>: <value>,
    ...
  }

============== ======================
VNC Attributes Description           
============== ======================
host           The vncprocy host
port           vncprocy port
password       Temporary password
type           Connection type (only VNC)
============== ======================

**Example Action Console Response: JSON**:

.. code-block:: javascript

  {
    "console": {
      "type": "vnc",
      "host": "vm42.example.org",
      "port": 1234,
      "password": "513NR14PN0T"
    }
  }

Set Server Firewall Profile
...........................

The firewallProfile function sets a firewall profile for the public interface
of a server.

Request body contents::

  firewallProfile: { profile: <firewall profile>}

* **firewall profile** can be ``ENABLED``, ``DISABLED`` or ``PROTECTED``

**Example Action firewallProfile: JSON**:

.. code-block:: javascript

  {"firewallProfile": {"profile": "ENABLED"}}

.. note:: Response body should be empty

OS/Compute Specific
...................

The following operations are meaningless or not supported in the context of
Synnefo/Cyclades, but are parts of the OS/Compute API:

* `Change Administrator Password <http://docs.openstack.org/api/openstack-compute/2/content/Change_Password-d1e3234.html>`_
* `Rebuild Server <http://docs.openstack.org/api/openstack-compute/2/content/Rebuild_Server-d1e3538.html>`_
* `Resize Server <http://docs.openstack.org/api/openstack-compute/2/content/Resize_Server-d1e3707.html>`_
* `Confirm Resized Server <http://docs.openstack.org/api/openstack-compute/2/content/Confirm_Resized_Server-d1e3868.html>`_
* `Revert Resized Server <http://docs.openstack.org/api/openstack-compute/2/content/Revert_Resized_Server-d1e4024.html>`_
* `Create Image <http://docs.openstack.org/api/openstack-compute/2/content/Create_Image-d1e4655.html>`_


Flavors
-------

A flavor is a hardware configuration for a server.

List Flavors
............

List the flavors that are accessible by the user

.. rubric:: Request

=================== ====== ======== ==========
URI                 Method Cyclades OS/Compute
=================== ====== ======== ==========
``/flavors``        GET    ✔        ✔
``/flavors/detail`` GET    ✔        **✘**
=================== ====== ======== ==========

* The detailed (``/flavors/detail``) listing in Cyclades is semantically
  similar to OS/Compute regular (``/flavor``) listing. The Cyclades regular
  listing semantics are Cyclades specific.

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

================= ===============
Request Parameter Value          
================= ===============
json              Respond in json
xml               Respond in xml 
================= ===============

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Forbidden to use this flavor
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Response code contents::

  flavors: {values[
    {
      <flavor attribute>: <value>,
      ...
    },
    ...
  ]}

Flavor attributes are `listed here <#flavor-ref>`_. Regular listing contains
only ``id`` and ``name`` attributes.

**Example List Flavors (regular): JSON**

.. code-block:: javascript

  {
    "flavors": {
      "values": [
        {
          "id": 1,
          "name": "One code",
        }, {
          "id": 3,
          "name": "Four core",
        }
      ]
    }
  }


**Example List Flavors (regular): XML**

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <flavors xmlns="http://docs.openstack.org/compute/api/v1"
    xmlns:atom="http://www.w3.org/2005/Atom">
    <flavor id="1" name="One core"/>
    <flavor id="3" name="Four core"/>
  </flavors>

**Example List Flavors (detail): JSON**

.. code-block:: javascript

  {
    "flavors": {
      "values": [
        {
          "id": 1,
          "name": "One core",
          "ram": 1024,
          "SNF:disk_template": "drbd",
          "disk": 20,
          "cpu": 1
        }, {
          "id": 3,
          "name": "Four core",
          "ram": 1024,
          "SNF:disk_template": "drbd",
          "disk": 40,
          "cpu": 4
        }
      ]
    }
  }

.. note:: In Compute OS API, the ``values`` layer is missing from the response

Get Flavor Details
..................

Get the configuration of a specific flavor

.. rubric:: Request

======================= ====== ======== ==========
URI                     Method Cyclades OS/Compute
======================= ====== ======== ==========
``/flavors/<flavor-id`` GET    ✔        ✔
======================= ====== ======== ==========

* **flavor-id** is the identifier of the flavor

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

================= ===============
Request Parameter Value          
================= ===============
json              Respond in json
xml               Respond in xml 
================= ===============

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed flavor ID
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Forbidden to use this flavor
404 (Not Found)             Flavor id not founmd
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Response code contents::

  flavor: {
    <flavor attribute>: <value>,
    ...
  }

All flavor attributes are `listed here <flavor-ref>`_.

**Example Flavor Details: JSON**

.. code-block:: javascript
  
  {
    "flavor": {
      {
        "id": 1,
        "name": "One core",
        "ram": 1024,
        "SNF:disk_template": "drbd",
        "disk": 20,
        "cpu": 1
      }
    }
  }

**Example Flavor Details: XML**

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <flavor xmlns="http://docs.openstack.org/compute/api/v1"
    xmlns:atom="http://www.w3.org/2005/Atom"
    id="1" name="One core" ram="1024" disk="20" cpu="1" />

Images
------

An image is a collection of files used to create or rebuild a server. Synnefo
deployments usually provide pre-built OS images, but custom image creation is
also supported.

List Images
...........

List all images accessible by the user

.. rubric:: Request

=================== ====== ======== ==========
URI                 Method Cyclades OS/Compute
=================== ====== ======== ==========
``/servers``        GET    ✔        ✔
``/servers/detail`` GET    ✔        ✔
=================== ====== ======== ==========

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

================= ======================== ======== ==========
Request Parameter Value                    Cyclades OS/Compute
================= ======================== ======== ==========
server            Server filter            **✘**    ✔
name              Image name filter        **✘**    ✔
status            Server status filter     **✘**    ✔
changes-since     Change timestamp filter  ✔        ✔
marker            Last list last ID filter **✘**    ✔
limit             Page size filter         **✘**    ✔
type              Request filter type      **✘**    ✔
================= ======================== ======== ==========

* **changes-since** must be an ISO8601 date string. In Cyclades it refers to
  the image ``updated_at`` attribute and it should be a date in the window
  [- POLL_LIMIT ... now]. POLL_LIMIT default value is 3600 seconds except if it
  is set otherwise at server side.

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
304 (No images since date)  Can be returned if ``changes-since`` is given
400 (Bad Request)           Invalid or malformed ``changes-since`` parameter
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Response body contents::

  images: {values: [
    {
      <image attribute>: <value>,
      ...
      metadata: {values: {
        <image metadatum key>: <value>,
        ...
      }},
      ...
    },
    ...
  ]}

The regular response returns just ``id`` and ``name``, while the detail returns a collections of the `image attributes listed here <#image-ref>`_.

**Example List Image (detail): JSON**

.. code-block:: javascript

  {
    "images: {
      "values": [
        {
          "status": "ACTIVE",
          "updated": "2013-03-02T15:57:03+00:00",
          "name": "edx_saas",
          "created": "2013-03-02T12:21:00+00:00",
          "progress": 100,
          "id": "175716...526236",
          "metadata": {
            "values": {
              "partition_table": "msdos",
              "osfamily": "linux",
              "users": "root saasbook",
              "exclude_task_changepassword": "yes",
              "os": "ubuntu",
              "root_partition": "1",
              "description": "Ubuntu 12.04 LTS"
            }
          }
        }, {
          "status": "ACTIVE",
          "updated": "2013-03-02T15:57:03+00:00",
          "name": "edx_saas",
          "created": "2013-03-02T12:21:00+00:00",
          "progress": 100,
          "id": "1357163d...c526206",
          "metadata": {
            "values": {
              "partition_table": "msdos",
              "osfamily": "windows",
              "users": "Administratior",
              "exclude_task_changepassword": "yes",
              "os": "WinME",
              "root_partition": "1",
              "description": "Rerto Windows"
            }
          }
        }
      ]
    }
  }

.. note:: In Compute OS API, the ``values`` layer is missing from the response

Get Image Details
.................

Get the details of a specific image

.. rubric:: Request

====================== ====== ======== ==========
URI                    Method Cyclades OS/Compute
====================== ====== ======== ==========
``/images/<image-id>`` GET    ✔        ✔
====================== ====== ======== ==========

* **image-id** is the identifier of the virtual image

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed image id
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to use this image
404 (Not Found)             Image not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   No available backends or service currently
\                           unavailable
=========================== =====================

Response body contents::

  image: {
    <image attribute>: <value>,
    ...
    metadata: {values:{
      <image metadatum key>: <value>
    }}
  }

Image attributes are `listed here <#image-ref>`_.

**Example Details for an image with id 6404619d-...-aef57eaff4af, in JSON**

.. code-block:: javascript

    {
    "image": {
      "id": "6404619d-...-aef57eaff4af",
      "name": "FreeBSD",
      "status": "ACTIVE",
      "updated": "2013-04-24T12:06:02+00:00",
      "created": "2013-04-24T11:52:16+00:00",
      "progress": 100,
      "metadata": {
        "values": {
          "kernel": "9.1 RELEASE",
          "osfamily": "freebsd",
          "users": "root",
          "gui": "No GUI",
          "sortorder": "9",
          "os": "freebsd",
          "root_partition": "2",
          "description": "FreeBSD 9"
        }
      }
    }
  }

.. note:: In OS/Compute API, the ``values`` layer is missing


Delete Image
............

Delete an image, by changing its status from ``ACTIVE`` to ``DELETED``.

.. rubric:: Request

====================== ====== ======== =========
URI                    Method Cyclades OS/Compute
====================== ====== ======== =========
``/images/<image id>`` DELETE ✔        ✔
====================== ====== ======== ==========

* **image id** is the identifier of the image

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Invalid request or image id
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Image not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   Action not supported or service currently
\                           unavailable
=========================== =====================

.. note:: In case of a 204 code, request body should be empty

Image Metadata
--------------

List metadata
.............

.. note:: This operation is semantically equivalent in Cyclades and OS/Compute
  besides the different URI.

=============================== ====== ======== ==========
URI                             Method Cyclades OS/Compute
=============================== ====== ======== ==========
``/images/<image-id>/meta``     GET    ✔        **✘**
``/images/<image-id>/metadata`` GET    **✘**    ✔
=============================== ====== ======== ==========

* **image-id** is the identifier of the virtual image

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Request succeeded
400 (Bad Request)           Invalid image ID or Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Server not found
409 (Build In Progress)     The image is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

In case of a 201 response code, the response should contain a JSON encoded list
of ``key``:``value`` pairs, under a 'values' tag which lies under a
``metadata`` tag, e.g.:

.. code-block:: javascript

  { 
    "metadata": {
      "values": {
        "partition_table": "msdos",
        "kernel": "3.2.0",
        "osfamily": "linux",
        "users": "user",
        "gui": "Unity 5",
        "sortorder": "3",
        "os": "ubuntu",
        "root_partition": "1",
        "description": "Ubuntu 12 LTS"
      }
    }
  }

.. note:: In OS/Compute API  the ``values`` level is missing from the response

Set / Update Image Metadata
...........................

In Cyclades API, setting new metadata and updating the values of existing ones
is achieved with the same type of request (POST), while in OS/Compute API there
are two separate request types (PUT and POST for
`setting new <http://docs.openstack.org/api/openstack-compute/2/content/Create_or_Replace_Metadata-d1e5358.html>`_
and
`updating existing <http://docs.openstack.org/api/openstack-compute/2/content/Update_Metadata-d1e5208.html>`_
metadata, respectively).

In Cyclades API, unmentioned metadata keys will remain intact, while metadata
referred by the operation will be overwritten.

=============================== ====== ======== ==========
URI                             Method Cyclades OS/Compute
=============================== ====== ======== ==========
``/images/<image-id>/meta``     POST    ✔       **✘**
``/images/<image-id>/metadata`` PUT    **✘**    ✔
``/images/<image-id>/metadata`` POST   **✘**    ✔
=============================== ====== ======== ==========

* **image-id** is the identifier of the virtual image

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

The request body should contain a JSON-formated set of ``key``:``value`` pairs,
under the ``metadata`` tag, e.g.::

  {'metadata': {'XtraSoftware': 'XampleSoft', 'os': 'Xubuntu'}}

|

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or image id
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this image
404 (Not Found)             Image or metadatum key not found
413 (OverLimit)             Maximum number of metadata exceeded
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

|

In case of a 201 code, the response body should present the new state of
servers metadata. E.g.::

  { 
    'metadata': {
      "partition_table": "msdos",
      "kernel": "3.2.0",
      "osfamily": "linux",
      "users": "user",
      "gui": "Unity 5",
      "sortorder": "3",
      "os": "Xubuntu",
      "root_partition": "1",
      "description": "Ubuntu 12 LTS",
      "XtraSoftware": "XampleSoft"
    }
  }

Get Metadata Item
.................

.. note:: This operation is semantically equivalent in Cyclades and OS/Compute
  besides the different URI.

===================================== ====== ======== ==========
URI                                   Method Cyclades OS/Compute
===================================== ====== ======== ==========
``/image/<image-id>/meta/<key>``      GET    ✔        **✘**
``/images/<image-id>/metadata/<key>`` GET    **✘**    ✔
===================================== ====== ======== ==========

* **image-id** is the identifier of the image

* **key** is the key of a matadatum ``key``:``value`` pair

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or image id
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to access this information
404 (Not Found)             Metadatum key not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

If the response code is 200, the response body contains the requested
``key``:``value`` pair under a ``metadata`` tag. For example, if key was
``os``, the response body would look similar to this:

.. code-block:: javascript

  {"metadata": {"os": "Xubuntu"}}

.. note:: In OS/Compute, ``metadata`` is ``meta``

Set / Update Metadatum Item
...........................

.. note:: This operation is semantically equivalent in Cyclades and OS/Compute
  besides the different URI.

===================================== ====== ======== ==========
URI                                   Method Cyclades OS/Compute
===================================== ====== ======== ==========
``/images/<image-id>/meta/<key>``     PUT    ✔        **✘**
``/images/<image-id>/metadata/<key>`` PUT    **✘**    ✔
===================================== ====== ======== ==========

* **image-id** is the identifier of the image

* **key** is the key of a matadatum ``key``:``value`` pair

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

Request body should contain a ``key``:``value`` pair under a ``meta`` tag. The
``value`` is the (new) value to set. The ``key`` of the metadatum may or may
not exist prior to the operation. For example, request with ``os`` as a ``key``
may contain the following request body::

  {'meta': {'os': 'Kubuntu'}}

|

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or image id
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this image
404 (Not Found)             Metadatum key not found
413 (OverLimit)             Maximum number of metadata exceeded
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

|

If the response code is 201, the response body contains the ``key``:``value``
pair that has just been created or updated, under a ``meta`` tag, so that the
body of the response is identical to the body of the request.

Delete Image Metadata
.....................

.. note:: This operation is semantically equivalent in Cyclades and OS/Compute
  besides the different URI.

===================================== ====== ======== ==========
URI                                   Method Cyclades OS/Compute
===================================== ====== ======== ==========
``/images/<image-id>/meta/<key>``     DELETE ✔        **✘**
``/images/<image-id>/metadata/<key>`` DELETE **✘**    ✔
===================================== ====== ======== ==========

* **image-id** is the identifier of the image
* **key** is the key of a matadatum ``key``:``value`` pair

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Malformed image ID
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this image
404 (Not Found)             Metadatum key not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================


Networks
--------

============= ======== ==========
BASE URI      Cyclades OS/Compute
============= ======== ==========
``/networks`` ✔        **✘**
============= ======== ==========

The Network part of Cyclades API is not supported by the OS/Compute API,
although it shares some similaritied with the
`OS Quantum API <http://docs.openstack.org/api/openstack-network/1.0/content/API_Operations.html>`_.
There are key differences in the design of the two systems, which exceed the
scope of this document, although they affect the respective APIs.

A Server can connect to one or more networks identified by a numeric id.
Networks are accessible only by the users who created them. When a network is
deleted, all connections to it are deleted.

There is a special **public** network with the id *public* that can be accessed
at */networks/public*. All servers are connected to **public** by default and
this network can not be deleted or modified in any way.

List Networks
.............

This operation lists the networks associated with a users account

==================== ======
URI                  Method
==================== ======
``/networks``        GET
``/networks/detail`` GET
==================== ======

|

==============  =========================
Request Header  Value                    
==============  =========================
X-Auth-Token    User authentication token
==============  =========================

|

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
304 (Not Modified)          
400 (Bad Request)           Malformed network id
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Network not found
409 (Build In Progress)     Server is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   Action not supported or service currently
\                           unavailable
=========================== =====================

The ``detail`` operation lists the `full network attributes <#network-ref>`_,
while the regular operation returns only the network ``id`` and ``name``.

**Example Networks List Response: JSON (regular)**:

.. code-block:: javascript

  {
    "networks": {
      "values": [
        {"id": "1". "name": "public"},
        {"id": "2". "name": "my private network"}
      ]
    }
  }

**Example Networks List Response: JSON (detail)**:

.. code-block:: javascript

  {
    "networks": {
      "values": [
        {
          "id": "1",
          "name": "public",
          "created": "2011-04-20T15:31:08.199640+00:00",
          "updated": "2011-05-06T12:47:05.582679+00:00",
          "attachments": {"values": ["nic-42-0", "nic-73-0"]}
        }, {
          "id": 2,
          "name": "my private network",
          "created": "2011-04-20T14:32:08.199640+00:00",
          "updated": "2011-05-06T11:40:05.582679+00:00",
          "attachments": {"values": ["nic-42-2", "nic-7-3"]}
        }
      ]
    }
  }


Create Network
..............

This operation creates a new network

==================== ======
URI                  Method
==================== ======
``/networks``        POST
==================== ======

|

==============  =========================
Request Header  Value                    
==============  =========================
X-Auth-Token    User authentication token
==============  =========================

|

The request body is json-formated and contains a collection of attributes under
the ``network`` tag, which are presented bellow:

================== ======================= ======== =======
Request Attributes Description             Required Default
================== ======================= ======== =======
name               Network name            ✔        
type               Network type            ✔
dhcp               If use DHCP             **✘**    True
cidr               IPv4 CIDR               **✘**    192.168.1.0/2
cidr6              IPv6 CDIR               **✘**    null
gateway            IPv4 gateway address    **✘**    null
gateway6           IPv6 gateway address    **✘**    null
public             If a public network     **✘**    False
================== ======================= ======== =======

* **name** is a string

* **type** can be CUSTOM, IP_LESS_ROUTED, MAC_FILTERED, PHYSICAL_VLAN

* **dhcp** and **public** are flags

* **cidr**, and **gateway** are IPv4 addresses

* **cidr6**, and **gateway6** are IPv6 addresses

* **public** should better not be used. If True, a 403 error is returned.

**Example Create Network Request Body: JSON**:

.. code-block:: javascript

  {"network": {"name": "private_net", "type": "MAC_FILTERED"}}

|

=========================== =====================
Return Code                 Description
=========================== =====================
202 (OK)                    Request succeeded
400 (Bad Request)           Malformed network id or request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Public network is forbidden
404 (Not Found)             Network not found
413 (Over Limit)            Reached networks limit
415 (Bad Media Type)        Bad network type
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   Failed to allocated network resources
=========================== =====================

In case of a 202 code, the operation asynchronously provisions a new private
network and the response body consists of a collection of 
`network attributes <#network-red>`_.

**Example Create Network Response: JSON**:

.. code-block:: javascript

  {
    "network": {
      "status": "PENDING",
      "updated": "2013-04-25T13:31:17.165237+00:00",
      "name": "my private network",
      "created": "2013-04-25T13:31:17.165088+00:00",
      "cidr6": null,
      "id": "6567",
      "gateway6": null,
      "public": false,
      "dhcp": false,
      "cidr": "192.168.1.0/24",
      "type": "MAC_FILTERED",
      "gateway": null,
      "attachments": {"values": []}
    }
  }


Get Network Details
...................

========================== ======
URI                        Method
========================== ======
``/networks/<network-id>`` GET   
========================== ======

* **network-id** is the identifier of the network

|

==============  =========================
Request Header  Value                    
==============  =========================
X-Auth-Token    User authentication token
==============  =========================

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or network id
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Network not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================

|

In case of a 200 code, the response body consists of a collection of
`network attributes <#network-ref>`_.

**Example Get Network Details Response: JSON**:

.. code-block:: javascript

  {
    "network": {
      "status": "PENDING",
      "updated": "2013-04-25T13:31:17.165237+00:00",
      "name": "my private network",
      "created": "2013-04-25T13:31:17.165088+00:00",
      "cidr6": null,
      "id": "6567",
      "gateway6": null,
      "public": false,
      "dhcp": false,
      "cidr": "192.168.1.0/24",
      "type": "MAC_FILTERED",
      "gateway": null,
      "attachments": {"values": []}
    }
  }

Rename Network
..............

========================== ======
URI                        Method
========================== ======
``/networks/<network-id>`` PUT   
========================== ======

* **network-id** is the identifier of the network

|

==============  =========================
Request Header  Value                    
==============  =========================
X-Auth-Token    User authentication token
==============  =========================

|

The request body is json-formated and contains a ``network`` tab over the
following attribute:

================== ================
Request Parameters Description
================== ================
name               New network name
================== ================

**Example Update Network Name Request: JSON**:

.. code-block:: javascript

  {"network": {"name": "new_name"}}

|

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or network deleted
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Network not found
413 (Over Limit)            Network Limit Exceeded
415 (Bad Media Type)        Bad network type
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================

In case of a 200 response code, the ``name`` of the network is changed to the
new value.

Delete Network
..............

========================== ======
URI                        Method
========================== ======
``/networks/<network-id>`` DELETE   
========================== ======

* **network-id** is the identifier of the network

|

==============  =========================
Request Header  Value                    
==============  =========================
X-Auth-Token    User authentication token
==============  =========================

|

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or network already deleted
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Network not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================

Add / Remove Server
...................

================================= ======
URI                               Method
================================= ======
``/networks/<network-id>/action`` POST
================================= ======

* **network-id** is the identifier of the network

|

==============  =========================
Request Header  Value                    
==============  =========================
X-Auth-Token    User authentication token
==============  =========================

|

The json-formated request body should be an ``add`` **or** ``remove`` tag over
the following attribute:

================== =================================
Request Paramenter Description
================== =================================
serverRef          Server id to (dis)connect from/to
================== =================================

**Example Action Add (connect to): JSON**:

.. code-block:: javascript

  {"add" : {"serverRef" : 42}}

**Example Action Remove (disconnect from): JSON**:

.. code-block:: javascript

  {"remove" : {"serverRef" : 42}}

|

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or network already deleted
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this network (e.g. public)
404 (Not Found)             Network not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================

In case of 204 code, the server is connected to (``add``) or disconnected from
(``remove``) the network.

Index of Attributes
-------------------

.. _server-ref:

Server Attributes
.................

================ ========================== ======== ==========
Server attribute Description                Cyclades OS/Compute
================ ========================== ======== ==========
id               Server ID                  ✔        ✔
name             Server Name                ✔        ✔
status           Server Status              ✔        ✔
updated          Date of last modification  ✔        ✔
created          Date of creation           ✔        ✔
hostId           Physical host              empty    ✔
imageRef         Image ID                   ✔        **✘**
image            A full image descreption   **✘**    ✔
flavorRef        Flavor ID                  ✔        **✘**
flavor           A full flavor description  **✘**    ✔
adminPass        Superuser Password         ✔        ✔
suspended        If server is suspended     ✔        ✔
progress         Build progress             ✔        ✔
metadata         Custom server metadata     ✔        ✔
user_id          Server owner               **✘**    ✔
tenant_id        Server tenant              **✘**    ✔
accessIPv4       Server IPV4 net address    **✘**    ✔
accessIPv6       Server IPV4 net address    **✘**    ✔
addresses        Nets connected on server   **✘**    ✔
links            Server links               **✘**    ✔
================ ========================== ======== ==========

* **status** values are described `here <#status-ref>`_

* **updated** and **created** are date-formated

* **hostId** is always empty in Cyclades and is returned for compatibility reasons

* **imageRef** and **flavorRef** always refer to existing Image and Flavor specifications. Cyclades improved the OpenStack approach by using references to Image and Flavor attributes, instead of listing their full properties

* **adminPass** in Cyclades it is generated automatically during creation. For safety, it is not stored anywhere in the system and it cannot be recovered with a query request

* **suspended** is True only of the server is suspended by the cloud administrations or policy

* **progress** is a number between 0 and 100 and reflects the server building status

* **metadata** are custom key:value pairs refering to the VM. In Cyclades, the ``OS`` and ``users`` metadata are automatically retrieved from the servers image during creation

.. _status-ref:

Server Status
.............

============= ==================== ======== ==========
Status        Description          Cyclades OS/Compute
============= ==================== ======== ==========
BUILD         Building             ✔        ✔
ACTIVE        Up and running       ✔        ✔
STOPPED       Shut down            ✔        **✘**
REBOOT        Rebooting            ✔        ✔
DELETED       Removed              ✔        ✔
UNKNOWN       Unexpected error     ✔        ✔
ERROR         In error             ✔        ✔
HARD_REBOOT   Hard rebooting       **✘**    ✔
PASSWORD      Resetting password   **✘**    ✔
REBUILD       Rebuilding server    **✘**    ✔
RESCUE        In rescue mode       **✘**    ✔
RESIZE        Resizing             **✘**    ✔
REVERT_RESIZE Failed to resize     **✘**    ✔
SHUTOFF       Shut down by user    **✘**    ✔
SUSPENDED     Suspended            **✘**    ✔
VERIFY_RESIZE Waiting confirmation **✘**    ✔
============= ==================== ======== ==========

.. _network-ref

Network
.......

.. note:: Networks are features in Cyclades API but not in OS/Compute API

================== ===========
Network Attributes Description
================== ===========
id                 Network identifier
name               Network name
created            Date of creation
updates            Date of last update
cidr               IPv4 CIDR Address
cidr6              IPv6 CIDR Address
dhcp               IPv4 DHCP Address
dhcp6              IPv6 DHCP Address
gateway            IPv4 Gateway Address
gateway6           IPv6 Gateway Address
public             If the network is public
status             Network status
attachments        Network Interface Connections (NICs)
================== ===========

* **id** and **name** are int and string respectively

* **created** and **updated** are ISO8061 date strings

* **public** is a boolean flag

* **status** can be PENDING, ACTIVE or DELETED

* **attachments** refers to the NICs connecting servers on that network.

.. _nic-ref:

Network Interface Connection (NIC)
..................................

A Network Interface Connection (NIC) represents a servers connection to a network.

A NIC is identified by a server and an (obviously unique) mac address. A server can have multiple NICs, though. In practice, a NIC id is used of reference and identification.

Each NIC is used to connect a specific server to a network. The network is aware of that connection for as long as it holds. If a NIC is disconnected from a network, it is destroyed.

A NIC specification contains the following information:

================= ====================== ======== ==========
Server Attributes Description            Cyclades OS/Compute
================= ====================== ======== ==========
id                The NIC id             ✔        **✘**
mac_address       NIC's mac address      ✔        **✘**
network_id        Network of connection  ✔        **✘**
firewallProfile   The firewall profile   ✔        **✘**
ipv4              IP v4 address          ✔        **✘**
ipv6              IP v6 address          ✔        **✘**
================= ====================== ======== ==========

* **id** is the unique identified of the NIC. It consists of the server id and an ordinal number nic-<server-id>-<ordinal number> , e.g. for a server with id 42::
  nic-42-0, nic-42-1, ...

* **mac_address** is the unique mac address of the interface

* **network_id** is the id of the network this nic connects to.

* **firewallProfile** , if set, refers to the mode of the firewall. Valid firewall profile values::

  ENABLED, DISABLED, PROTECTED

* **ipv4** and **ipv6** are the IP addresses (versions 4 and 6 respectively) of the specific network connection for that machine.

.. _flavor-ref:

Flavor
......

A flavor is a hardware configuration for a server. It contains the following
information:

================= ==================== ======== ==========
Flavor Attributes Description          Cyclades OS/Compute
================= ==================== ======== ==========
id                The flavor id        ✔        ✔
name              The flavor name      ✔        ✔
ram               Server RAM size      ✔        ✔
SNF:disk_template Storage mechanism    ✔        **✘**
disk              Server disk size     ✔        ✔
cpu               # of Virtual CPUs    ✔        **✘**
vcpus             # of Virtual CPUs    **✘**    ✔
links rel         Atom link rel field  **✘**    ✔
links href        Atom link href field **✘**    ✔
================= ==================== ======== ==========

* **id** is the flavor unique id (a possitive integer)

* **name** is the flavor name (a string)

* **ram** is the server RAM size in MB

* **SNF:disk_template** is a reference to the underlying storage mechanism used
by the Cyclades server. It is Cyclades specific.

* **disk** the servers disk size in GB

* **cpu** and **vcpus** are semantically equivalent terms in Cyclades and OS/Compute APIs respectively and they refer to the number of virtual CPUs assigned
to a server

* **link ref** and **link href** refer to the Atom link attributes that are
`used in OS/Compute API <http://docs.openstack.org/api/openstack-compute/2/content/List_Flavors-d1e4188.html>`_.

.. _image-ref:

Image
.....

An image is a collection of files you use to create or rebuild a server.

An image item may have the fields presented bellow:

================= ====================== ======== ==========
Server Attributes Description            Cyclades OS/Compute
================= ====================== ======== ==========
id                Image ID               ✔        ✔
name              Image name             ✔        ✔
updated           Last update date       ✔        ✔
created           Image creation date    ✔        ✔
progress          Ready status progress  ✔        **✘**
status            Image status           **✘**    ✔
tenant_id         Image creator          **✘**    ✔
user_id           Image users            **✘**    ✔
metadata          Custom metadata        ✔        ✔
links             Atom links             **✘**    ✔
minDisk           Minimum required disk  **✘**    ✔
minRam            Minimum required RAM   **✘**    ✔
================= ====================== ======== ==========

* **id** is the image id and **name** is the image name. They are both strings.

* **updated** and **created** are both ISO8601 date strings

* **progress** varies between 0 and 100 and denotes the status of the image

* **metadata** is a collection of ``key``:``values`` pairs of custom metadata,
under the tag ``values`` which lies under the tag ``metadata``.

.. note:: in OS/Compute, the ``values`` layer is missing
