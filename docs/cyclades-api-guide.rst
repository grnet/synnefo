.. _cyclades-api-guide:

API Guide
*********

`Cyclades <cyclades.html>`_ is the Compute Service of `Synnefo
<http://www.synnefo.org>`_. The Cyclades API tries to be as close to the
`OpenStack Compute API v2
<http://docs.openstack.org/api/openstack-compute/2/content>`_ as possible.

This document's goals are:

* Define the Cyclades/Compute REST API
* Clarify the differences between Cyclades and OpenStack/Compute

Users and developers who wish to access Cyclades through its REST API are
advised to use the `kamaki <http://www.synnefo.org/docs/kamaki/latest/index.html>`_ command-line
client and associated python library, instead of making direct calls.

Overview
========

* OpenStack does not define if requests for invalid URLs should return 404 or a
* Fault. We return a BadRequest Fault.
* OpenStack does not define if requests with a wrong HTTP method should return
* 405 or a Fault. We return a BadRequest Fault.

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

=================================================== ========================================= ====== ======== ==========
Description                                         URI                                       Method Cyclades OS/Compute
=================================================== ========================================= ====== ======== ==========
`List <#list-servers>`_                             ``/servers``                              GET    ✔        ✔
\                                                   ``/servers/detail``                       GET    ✔        ✔
`Create <#create-server>`_                          ``/servers``                              POST   ✔        ✔
`Get Stats <#get-server-stats>`_                    ``/servers/<server-id>/stats``            GET    ✔        **✘**
`Get Diagnostics <#get-server-diagnostics>`_        ``/servers/<server-id>/diagnostics``      GET    ✔        **✘**
`Get Details <#get-server-details>`_                ``/servers/<server id>``                  GET    ✔        ✔
`Rename <#rename-server>`_                          ``/servers/<server id>``                  PUT    ✔        ✔
`Delete <#delete-server>`_                          ``/servers/<server id>``                  DELETE ✔        ✔
`List Addresses <#list-server-addresses>`_          ``/servers/<server id>/ips``              GET    ✔        ✔
`Get NICs by Net <#get-server-nics-by-network>`_    ``/servers/<server id>/ips/<network id>`` GET    ✔        ✔
`List Metadata <#list-server-metadata>`_            ``/servers/<server-id>/metadata``         GET    ✔        ✔
`Update Metadata <#set-update-server-metadata>`_    ``/servers/<server-id>/metadata``         PUT    **✘**    ✔
\                                                   ``/servers/<server-id>/metadata``         POST   ✔        ✔
`Get Meta Item <#get-server-metadata-item>`_        ``/servers/<server-id>/metadata/<key>``   GET    ✔        ✔
`Update Meta Item <#update-server-metadatum-item>`_ ``/servers/<server-id>/metadata/<key>``   PUT    ✔        ✔
`Delete Meta Item <#delete-server-metadatum>`_      ``/servers/<server-id>/metadata/<key>``   DELETE ✔        ✔
=================================================== ========================================= ====== ======== ==========

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
flavor            The flavor id          ✔        ✔
image             The image id           ✔        ✔
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

*Example List Servers: JSON*

.. code-block:: javascript

  {
    "servers": [
      {
        "attachments": [
            {
              "id": "nic-42-0",
              "network_id": "101",
              "mac_address": "aa:00:00:49:2e:7e",
              "firewallProfile": "DISABLED",
              "ipv4": "192.168.4.5",
              "ipv6": "2001:648:2ffc:1222:a800:ff:fef5:3f5b"
            }
        ],
        "created': '2011-04-19T10:18:52.085737+00:00',
        "flavorRef": "1",
        "hostId": "",
        "id": "42",
        "imageRef": "3",
        "metadata": {{"foo": "bar"},
        "name": "My Server",
        "status": "ACTIVE",
        "updated": "2011-05-29T14:07:07.037602+00:00"
      }, {
        "attachments": [
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
        ],
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
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

*Example Request Headers*::

  X-Auth-Token:   z31uRXUn1LZy45p1r7V==
  Content-Type:   application/json
  Content-Length: 735

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
  injection is a way to add a file into a virtual server while creating it.
  Each change modifies/creates a file on the virtual server. The injected data
  (``contents``) should not exceed 10240 *bytes* in size and must be base64
  encoded. The file mode should be a number, not a string. A personality
  injection contains the following attributes:

====================== =================== ======== ==========
Personality Attributes Description         Cyclades OS/Compute
====================== =================== ======== ==========
path                   File path on server ✔        ✔
contents               Data to inject      ✔        ✔
group                  User group          ✔        **✘**
mode                   File access mode    ✔        **✘**
owner                  File owner          ✔        **✘**
====================== =================== ======== ==========

*Example Create Server Request: JSON*

.. code-block:: javascript

  {
    "server": {
      "name": "My Server Name: Example Name",
      "imageRef": "da7a211f-...-f901ce81a3e6",
      "flavorRef": 289,
      "personality": [
        {
          "path": "/Users/myusername/personlities/example1.file",
          "contents": "some data to inject",
          "group": "remotely-set user group",
          "mode": 0600,
          "owner": "ausername"
        }, {
          "path": "/Users/myusername/personlities/example2.file",
          "contents": "some more data to inject",
          "group": "",
          "mode": 0777,
          "owner": "anotherusername"
        }
      ],
      "metadata": {
        "EloquentDescription": "Example server with personality",
        "ShortDescription": "Trying VMs"
      }
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

*Example Create Server Response: JSON*

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
      "metadata": {
        "EloquentDescription": "Example server with personality",
        "ShortDescription": "Trying VMs"
      }
    }
  }

*Example Create Server Response: XML*

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

*Example Get Server Stats Response: JSON*

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

*Example Get Network Details Response: XML*

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

*Example Get Server Diagnostics Response: JSON*

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
flavor            The flavor id          ✔        ✔
image             The image id           ✔        ✔
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

*Example Details for server with id 42042: JSON*

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
      "attachments": [
        {
          "network_id": "1888",
          "mac_address": "aa:0c:f5:ad:16:41",
          "firewallProfile": "DISABLED",
          "ipv4": "83.212.112.56",
          "ipv6": "2001:648:2ffc:1119:a80c:f5ff:fead:1641",
          "id": "nic-42042-0"
        }
      ],
      "suspended": false,
      "diagnostics": [
        {
          "level": "DEBUG",
          "created": "2013-04-18T10:09:52.776920+00:00",
          "source": "image-info",
          "source_date": "2013-04-18T10:09:52.709791+00:00",
          "message": "Image customization finished successfully.",
          "details": null
        }
      ],
      "progress": 100,
      "metadata": {
        "OS": "windows",
        "users": "Administrator"
      }
    }
  }

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
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

**Example Request Headers**::

  X-Auth-Token:   z31uRXUn1LZy45p1r7V==
  Content-Type:   application/json
  Content-Length: 54

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

*Example Rename Server Request: JSON*

.. code-block:: javascript

  {"server": {"name": "A new name for my virtual server"}}

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

  addresses: [
    {
      <NIC attribute>: <value>,
      ...
    },
    ...
  ]

A Network Interface Connection (or NIC) connects the current server to a
network, through their respective identifiers. More information in NIC
attributes are `enlisted here <#nic-ref>`_.

*Example List Addresses: JSON*

.. code-block:: javascript

  {
    "addresses": [
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
``/servers/<server-id>/metadata`` GET    ✔        ✔
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

  metadata: {
    <key>: <value>,
      ...
  }

*Example List Server Metadata: JSON*

.. code-block:: javascript

  {
    ""metadata": {
      "OS": "Linux",
      "users": "root"
    }
  }

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
``/servers/<server-id>/metadata`` PUT    **✘**    ✔
``/servers/<server-id>/metadata`` POST   ✔       ✔
================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

**Example Request Headers**::

  X-Auth-Token:   z31uRXUn1LZy45p1r7V==
  Content-Type:   application/json
  Content-Length: 56

.. note:: Request parameters should be empty

Request body contents::

  metadata: {
    <key>: <value>,
    ...
  }

*Example Request Set / Update Server Metadata: JSON*

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
    <key>: <value>,
    ...
  }

*Example Response Set / Update Server Metadata: JSON*

.. code-block:: javascript

  {"metadata": {"OS": "Linux", "role": "webmail", "users": "root,maild"}}

Get Server Metadata Item
........................

Get the value of a specific piece of metadata of a virtual server

.. rubric:: Request

======================================= ====== ======== ==========
URI                                     Method Cyclades OS/Compute
======================================= ====== ======== ==========
``/servers/<server-id>/metadata/<key>`` GET    ✔        ✔
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

  metadata: {<key>: <value>}

*Example Get Server Metadatum for Item 'role', JSON*

.. code-block:: javascript

  {"metadata": {"role": "webmail"}}

Update Server Metadatum Item
.............................

Set a new or update an existing a metadum value for a virtual server.

.. rubric:: Request

======================================= ====== ======== ==========
URI                                     Method Cyclades OS/Compute
======================================= ====== ======== ==========
``/servers/<server-id>/metadata/<key>`` PUT    ✔        ✔
======================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server

* **key** is the key of a ``key``:``value`` pair piece of metadata

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

**Example Request Headers**::

  X-Auth-Token:   z31uRXUn1LZy45p1r7V==
  Content-Type:   application/json
  Content-Length: 29

.. note:: Request parameters should be empty

Request body content::

  metadata: {<key>: <value>}

*Example Request to Set or Update Server Metadatum "role": JSON*

.. code-block:: javascript

  {"metadata": {"role": "gateway"}}

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

  metadata: {<key>: <value>}

*Example Set or Update Server Metadatum "role":"gateway": JSON*

.. code-block:: javascript

  {"metadata": {"role": "gateway"}}

Delete Server Metadatum
.......................

Delete a metadatum of a virtual server

.. rubric:: Request

======================================= ====== ======== ==========
URI                                     Method Cyclades OS/Compute
======================================= ====== ======== ==========
``/servers/<server-id>/metadata/<key>`` DELETE ✔        ✔
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

=============================================== ======== ==========
Operations                                      Cyclades OS/Compute
=============================================== ======== ==========
`Start <#start-server>`_                        ✔        **✘**
`Shutdown <#shutdown-server>`_                  ✔        **✘**
`Reboot <#reboot-server>`_                      ✔        ✔
`Get Console <#get-server-console>`_            ✔        **✘**
`Set Firewall <#set-server-firewall-profile>`_  ✔        **✘**
`Change Admin Password <#os-compute-specific>`_ **✘**    ✔
`Rebuild <#os-compute-specific>`_               **✘**    ✔
`Resize <#os-compute-specific>`_                **✘**    ✔
`Confirm Resized <#os-compute-specific>`_       **✘**    ✔
`Revert Resized <#os-compute-specific>`_        **✘**    ✔
`Create Image <#os-compute-specific>`_          **✘**    ✔
=============================================== ======== ==========

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
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

**Example Request Headers**::

  X-Auth-Token:   z31uRXUn1LZy45p1r7V==
  Content-Type:   application/json
  Content-Length: 32

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

*Example Start Server: JSON*

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
only the ``REBOOT`` term. The expected behavior is the same, though.

Request body contents::

  reboot: {type: <reboot type>}

* **reboot type** can be either ``SOFT`` or ``HARD``.

*Example (soft) Reboot Server: JSON*

.. code-block:: javascript

  {"reboot" : { "type": "soft"}}

.. note:: Response body should be empty

Shutdown server
...............

This operation transitions a server from an ACTIVE to a STOPPED state.

Request body contents::

  shutdown: {}

*Example Shutdown Server: JSON*

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

*Example Get Server Console: JSON*

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

*Example Action Console Response: JSON*

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

*Example Action firewallProfile: JSON**

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

==================================== ======================== ====== ======== ==========
Description                          URI                      Method Cyclades OS/Compute
==================================== ======================== ====== ======== ==========
`List <#list-flavors>`_              ``/flavors``             GET    ✔        ✔
\                                    ``/flavors/detail``      GET    ✔        **✘**
`Get details <#get-flavor-details>`_ ``/flavors/<flavor-id>`` GET    ✔        ✔
==================================== ======================== ====== ======== ==========

List Flavors
............

List the flavors that are accessible by the user

.. rubric:: Request

=================== ====== ======== ==========
URI                 Method Cyclades OS/Compute
=================== ====== ======== ==========
``/flavors``        GET    ✔        ✔
``/flavors/detail`` GET    ✔        ✔
=================== ====== ======== ==========

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

  flavors: [
    {
      <flavor attribute>: <value>,
      ...
    },
    ...
  ]

Flavor attributes are `listed here <#flavor-ref>`_. Regular listing contains
only ``id`` and ``name`` attributes.

*Example List Flavors (regular): JSON*

.. code-block:: javascript

  {
    "flavors": [
      {
        "id": 1,
        "name": "One code",
      }, {
        "id": 3,
        "name": "Four core",
      }
    ]
  }


*Example List Flavors (regular): XML*

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <flavors xmlns="http://docs.openstack.org/compute/api/v1"
    xmlns:atom="http://www.w3.org/2005/Atom">
    <flavor id="1" name="One core"/>
    <flavor id="3" name="Four core"/>
  </flavors>

*Example List Flavors (detail): JSON*

.. code-block:: javascript

  {
    "flavors": [
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

*Example Flavor Details: JSON*

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

*Example Flavor Details: XML*

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

============================================= ===================================== ====== ======== ==========
Description                                   URI                                   Method Cyclades OS/Compute
============================================= ===================================== ====== ======== ==========
`List <#list-images>`_                        ``/images``                           GET    ✔        ✔
\                                             ``/images/detail``                    GET    ✔        ✔
`Get details <#get-image-details>`_           ``/images/<image-id>``                GET    ✔        ✔
`Delete <#delete-image>`_                     ``/images/<image id>``                DELETE ✔        ✔
`List Metadata <#list-image-metadata>`_       ``/images/<image-id>/metadata``       GET    ✔        ✔
`Update Metadata <#update-image-metadata>`_   ``/images/<image-id>/metadata``       POST   ✔        ✔
\                                             ``/images/<image-id>/metadata``       PUT    **✘**    ✔
`Get Meta Item <#get-image-metadatum>`_       ``/image/<image-id>/metadata/<key>``  GET    ✔        ✔
`Update Metadatum <#update-image-metadatum>`_ ``/images/<image-id>/metadata/<key>`` PUT    ✔        ✔
`Delete Metadatum <#delete-image-metadatum>`_ ``/images/<image-id>/metadata/<key>`` DELETE ✔        ✔
============================================= ===================================== ====== ======== ==========


List Images
...........

List all images accessible by the user

.. rubric:: Request

=================== ====== ======== ==========
URI                 Method Cyclades OS/Compute
=================== ====== ======== ==========
``/images``        GET    ✔        ✔
``/images/detail`` GET    ✔        ✔
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

  images: [
    {
      <image attribute>: <value>,
      ...
      metadata: {
        <image metadatum key>: <value>,
        ...
      },
      ...
    },
    ...
  ]

The regular response returns just ``id`` and ``name``, while the detail returns
a collections of the `image attributes listed here <#image-ref>`_.

*Example List Image (detail): JSON*

.. code-block:: javascript

  {
    "images: [
      {
        "status": "ACTIVE",
        "updated": "2013-03-02T15:57:03+00:00",
        "name": "edx_saas",
        "created": "2013-03-02T12:21:00+00:00",
        "progress": 100,
        "id": "175716...526236",
        "metadata": {
          "partition_table": "msdos",
          "osfamily": "linux",
          "users": "root saasbook",
          "exclude_task_changepassword": "yes",
          "os": "ubuntu",
          "root_partition": "1",
          "description": "Ubuntu 12.04 LTS"
        }
      }, {
        "status": "ACTIVE",
        "updated": "2013-03-02T15:57:03+00:00",
        "name": "edx_saas",
        "created": "2013-03-02T12:21:00+00:00",
        "progress": 100,
        "id": "1357163d...c526206",
        "metadata": {
          "partition_table": "msdos",
          "osfamily": "windows",
          "users": "Administratior",
          "exclude_task_changepassword": "yes",
          "os": "WinME",
          "root_partition": "1",
          "description": "Rerto Windows"
        }
      }
    ]
  }

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
    metadata: {
      <image metadatum key>: <value>
    }
  }

Image attributes are `listed here <#image-ref>`_.

*Example Details for an image with id 6404619d-...-aef57eaff4af, in JSON*

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


Delete Image
............

Delete an image, by changing its status from ``ACTIVE`` to ``DELETED``.

.. rubric:: Request

====================== ====== ======== ==========
URI                    Method Cyclades OS/Compute
====================== ====== ======== ==========
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

List Image Metadata
...................

.. rubric:: Request

=============================== ====== ======== ==========
URI                             Method Cyclades OS/Compute
=============================== ====== ======== ==========
``/images/<image-id>/metadata`` GET    ✔        ✔
=============================== ====== ======== ==========

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

Response body content::

  metadata: {
    <metadatum key>: <value>,
  ...
  }

*Example List Image Metadata: JSON*

.. code-block:: javascript

  {
    "metadata": {
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

.. note:: In OS/Compute API  the ``values`` level is missing from the response.

Update Image Metadata
.....................

In Cyclades API, setting new metadata and updating the values of existing ones
is achieved using one type of request (POST), while in OS/Compute API two
different types are used (PUT and POST for
`setting new <http://docs.openstack.org/api/openstack-compute/2/content/Create_or_Replace_Metadata-d1e5358.html>`_
and
`updating existing <http://docs.openstack.org/api/openstack-compute/2/content/Update_Metadata-d1e5208.html>`_
metadata, respectively).

In Cyclades API, unmentioned metadata keys will remain intact, while metadata
referred by the operation will be overwritten.

.. rubric:: Request

=============================== ====== ======== ==========
URI                             Method Cyclades OS/Compute
=============================== ====== ======== ==========
``/images/<image-id>/metadata`` PUT    **✘**    ✔
``/images/<image-id>/metadata`` POST   ✔        ✔
=============================== ====== ======== ==========

* **image-id** is the identifier of the virtual image

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

**Example Request Headers**::

  X-Auth-Token:   z31uRXUn1LZy45p1r7V==
  Content-Type:   application/json
  Content-Length: 52

.. note:: Request parameters should be empty

Request body content::

  metadata: {
    <metadatum key>: <value>,
    ...
  }

*Example Update Image Metadata Request: JSON*

.. code-block:: javascript

  {"metadata": {"NewAttr": "NewVal", "os": "Xubuntu'}}

.. rubric:: Response

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

Response body content::

  metadata: {
    <key>: <value>,
    ...
  }

*Example Update Image Response: JSON*

.. code-block:: javascript

  {
    "metadata": {
      "partition_table": "msdos",
      "kernel": "3.2.0",
      "osfamily": "linux",
      "users": "user",
      "gui": "Unity 5",
      "sortorder": "3",
      "os": "Xubuntu",
      "root_partition": "1",
      "description": "Ubuntu 12 LTS",
      "NewAttr": "NewVal"
    }
  }

Get Image Metadatum
...................

.. rubric:: Request

===================================== ====== ======== ==========
URI                                   Method Cyclades OS/Compute
===================================== ====== ======== ==========
``/images/<image-id>/metadata/<key>`` GET    ✔        ✔
===================================== ====== ======== ==========

* **image-id** is the identifier of the image

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
400 (Bad Request)           Malformed request or image id
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to access this information
404 (Not Found)             Metadatum key not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Response body content::

  metadata: {<key>: <value>}

*Example Get Image Metadatum Item: JSON*

.. code-block:: javascript

  {"metadata": {"os": "Xubuntu"}}

.. note:: In OS/Compute, ``metadata`` is ``meta``

Update Image Metadatum
......................

.. rubric:: Request

===================================== ====== ======== ==========
URI                                   Method Cyclades OS/Compute
===================================== ====== ======== ==========
``/images/<image-id>/metadata/<key>`` PUT    ✔        ✔
===================================== ====== ======== ==========

* **image-id** is the identifier of the image

* **key** is the key of a matadatum ``key``:``value`` pair

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

**Example Request Headers**::

  X-Auth-Token:   z31uRXUn1LZy45p1r7V==
  Content-Type:   application/json
  Content-Length: 27

|

.. note:: Request parameters should be empty

Request body content::

  metadata: {<key>: <value>}

*Example Update Image Metadatum Item Request: JSON*

.. code-block:: javascript

  {"metadata": {"os": "Kubuntu"}}

.. rubric:: Response

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

Request body content::

  metadata: {<key>: <value>}

*Example Update Image Metadatum Item Response: JSON*

.. code-block:: javascript

  {"metadata": {"os": "Kubuntu"}}

Delete Image Metadatum
......................

Delete an image metadatum by its key.

.. rubric:: Request

===================================== ====== ======== ==========
URI                                   Method Cyclades OS/Compute
===================================== ====== ======== ==========
``/images/<image-id>/metadata/<key>`` DELETE ✔        ✔
===================================== ====== ======== ==========

* **image-id** is the identifier of the image

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
400 (Bad Request)           Malformed image ID
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this image
404 (Not Found)             Metadatum key not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

.. note:: In case of a 204 code, the response body should be empty.

Networks
--------

============= ======== ==========
BASE URI      Cyclades OS/Compute
============= ======== ==========
``/networks`` ✔        **✘**
============= ======== ==========

The Network part of Cyclades API is not supported by the OS/Compute API,
although it shares some similarities with the
`OS Quantum API <http://docs.openstack.org/api/openstack-network/1.0/content/API_Operations.html>`_.
There are key design differences between the two systems but they exceed the
scope of this document, although they affect the respective APIs.

A Server can connect to one or more networks identified by a numeric id.
Networks are accessible only by the users who created them. When a network is
deleted, all connections to it are deleted.

There is a special **public** network with the id *public* that can be accessed
at */networks/public*. All servers are connected to **public** by default and
this network can not be deleted or modified in any way.

=============================================== ================================= ======
Description                                     URI                               Method
=============================================== ================================= ======
`List <#list-networks>`_                        ``/networks``                     GET
\                                               ``/networks/detail``              GET
`Create <#create-network>`_                     ``/networks``                     POST
`Get details <#get-network-details>`_           ``/networks/<network-id>``        GET
`Rename <#rename-network>`_                     ``/networks/<network-id>``        PUT
`Delete <#delete-network>`_                     ``/networks/<network-id>``        DELETE
`Connect <#connect-network-to-server>`_         ``/networks/<network-id>/action`` POST
`Disconnect <#disconnect-network-from-server>`_ ``/networks/<network-id>/action`` POST
=============================================== ================================= ======


List Networks
.............

This operation lists the networks associated with a users account

.. rubric:: Request

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

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

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

Response body content::

  networks: [
    {
      <network attribute>: <value>,
      ...
    },
    ...
  }

The ``detail`` operation lists the `full network attributes <#network-ref>`_,
while the regular operation returns only the ``id`` and ``name`` attributes.

*Example Networks List Response: JSON (regular)*

.. code-block:: javascript

  {
    "networks": [
      {"id": "1", "name": "public"},
      {"id": "2", "name": "my private network"}
    ]
  }

*Example Networks List Response: JSON (detail)*

.. code-block:: javascript

  {
    "networks": [
      {
        "id": "1",
        "name": "public",
        "created": "2011-04-20T15:31:08.199640+00:00",
        "updated": "2011-05-06T12:47:05.582679+00:00",
        "attachments": ["nic-42-0", "nic-73-0"]
      }, {
        "id": 2,
        "name": "my private network",
        "created": "2011-04-20T14:32:08.199640+00:00",
        "updated": "2011-05-06T11:40:05.582679+00:00",
        "attachments": ["nic-42-2", "nic-7-3"]
      }
    ]
  }


Create Network
..............

This operation asynchronously provisions a new network.

.. rubric:: Request

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
Content-Type    Type or request body     
Content-Length  Length of request body   
==============  =========================

**Example Request Headers**::

  X-Auth-Token:   z31uRXUn1LZy45p1r7V==
  Content-Type:   application/json
  Content-Length: 60

.. note:: Request parameters should be empty

Request body content::

  network: {
    <request attribute>: <value>,
    ...
  }

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

*Example Create Network Request Body: JSON*

.. code-block:: javascript

  {"network": {"name": "private_net", "type": "MAC_FILTERED"}}

.. rubric:: Response

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

Response body content::

  network: {
    <network attribute>: <value>,
    ...
  }

A list of the valid network attributes can be found `here <#network-ref>`_.

*Example Create Network Response: JSON*

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
      "attachments": []
    }
  }

Get Network Details
...................

.. rubric:: Request

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

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

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

Response code content::

  network: {
    <network attribute>: <value>,
    ...
  }

A list of network attributes can be found `here <#network-ref>`_.

*Example Get Network Details Response: JSON*

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
      "attachments": []
    }
  }

Rename Network
..............

.. rubric:: Request

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
Content-Type    Type or request body
Content-Length  Length of request body
==============  =========================

**Example Request Headers**::

  X-Auth-Token:   z31uRXUn1LZy45p1r7V==
  Content-Type:   application/json
  Content-Length: 33

.. note:: Request parameters should be empty

Request body content::

  network: {name: <new value>}

*Example Update Network Name Request: JSON*

.. code-block:: javascript

  {"network": {"name": "new_name"}}

.. rubric:: Response

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

.. note:: In case of a 204 code, the response body should be empty

Delete Network
..............

A network is deleted as long as it is not attached to any virtual servers.

.. rubric:: Request

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

.. note:: Request parameters should be empty

.. note:: Request body should be empty

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or network already deleted
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Network not found
421 (Network In Use)        The network is in use and cannot be deleted
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================

.. note:: In case of a 204 code, the response body should be empty


Connect network to Server
..........................

Connect a network to a virtual server. The effect of this operation is the
creation of a NIC that connects the two parts.

.. rubric:: Request

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
Content-Type    Type or request body
Content-Length  Length of request body
==============  =========================

**Example Request Headers**::

  X-Auth-Token:   z31uRXUn1LZy45p1r7V==
  Content-Type:   application/json
  Content-Length: 28

.. note:: Request parameters should be empty

Response body content (connect)::

  add {serverRef: <server id to connect>}

*Example Action Add (connect to): JSON*

.. code-block:: javascript

  {"add" : {"serverRef" : 42}}

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
202 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or network already deleted
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this network (e.g. public)
404 (Not Found)             Network not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================

.. note:: In case of a 202 code, the request body should be empty

Disconnect network from Server
..............................

Disconnect a network from a virtual server. The effect of this operation is the
deletion of the NIC that connects the two parts.

.. rubric:: Request

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
Content-Type    Type or request body
Content-Length  Length of request body
==============  =========================

**Example Request Headers**::

  X-Auth-Token:   z31uRXUn1LZy45p1r7V==
  Content-Type:   application/json
  Content-Length: 31

.. note:: Request parameters should be empty

Response body content (disconnect)::

  remove {serverRef: <server id to disconnect>}

*Example Action Remove (disconnect from): JSON*

.. code-block:: javascript

  {"remove" : {"serverRef" : 42}}

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
202 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or network already deleted
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this network (e.g. public)
404 (Not Found)             Network not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================

.. note:: In case of a 202 code, the request body should be empty

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
image            A full image descreption   ✔        ✔
flavor           A full flavor description  ✔        ✔
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

* **image** and **flavor** always refer to existing Image and Flavor
  specifications.

* **adminPass** in Cyclades it is generated automatically during creation. For
  safety, it is not stored anywhere in the system and it cannot be recovered
  with a query request

* **suspended** is True only of the server is suspended by the cloud
  administrations or policy

* **progress** is a number between 0 and 100 and reflects the server building
  status

* **metadata** are custom key:value pairs refering to the VM. In Cyclades, the
  ``OS`` and ``users`` metadata are automatically retrieved from the servers
  image during creation

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

.. _network-ref:

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

A Network Interface Connection (NIC) represents a servers connection to a
network.

A NIC is identified by a server and an (obviously unique) mac address. A server
can have multiple NICs, though. In practice, a NIC id is used of reference and
identification.

Each NIC is used to connect a specific server to a network. The network is
aware of that connection for as long as it holds. If a NIC is disconnected from
a network, it is destroyed.

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

* **id** is the unique identified of the NIC. It consists of the server id and
  an ordinal number nic-<server-id>-<ordinal number> , e.g. for a server with
  id 42::

    nic-42-0, nic-42-1, ...

* **mac_address** is the unique mac address of the interface

* **network_id** is the id of the network this nic connects to.

* **firewallProfile** , if set, refers to the mode of the firewall. Valid
  firewall profile values::

    ENABLED, DISABLED, PROTECTED

* **ipv4** and **ipv6** are the IP addresses (versions 4 and 6 respectively) of
  the specific network connection for that machine.

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
vcpus             # of Virtual CPUs    ✔        ✔
links rel         Atom link rel field  **✘**    ✔
links href        Atom link href field **✘**    ✔
================= ==================== ======== ==========

* **id** is the flavor unique id (a possitive integer)

* **name** is the flavor name (a string)

* **ram** is the server RAM size in MB

* **SNF:disk_template** is a reference to the underlying storage mechanism
  used by the Cyclades server. It is Cyclades specific.

* **disk** the servers disk size in GB

* **vcpus** refer to the number of virtual CPUs assigned to a server

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
