.. _cyclades-api-guide:

API Guide
*********

`Cyclades <cyclades.html>`_ is the compute service developed by `GRNET 
<http://www.grnet.gr>`_ as part of the `synnefo <http://www.synnefo.org>`_
software, that implements an extension of the `OpenStack Compute API v2
<http://docs.openstack.org/api/openstack-compute/2/content>`_.

This document's goals are:

* Define the Cyclades/Compute ReST API
* Clarify the differences between Cyclades and OOS Compute

Users and developers who wish to access a synnefo Cyclades service through its
ReST API are adviced to use the `kamaki <http://docs.dev.grnet.gr/kamaki>`_
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

* Authentication support is missing.


Request/Response Types
----------------------

* We only support JSON Requests and JSON/XML Responses. XML Requests are not
  supported for now.


Content Compression
-------------------

* Optional content compression support is missing.


Persistent Connections
----------------------

* Deployment note: "To prevent abuse, HTTP sessions have a timeout of 20
  seconds before being closed."


Links and References
--------------------

* Full URI references support is missing.
* Self and bookmark links support is missing.


Paginated Collections
---------------------

* Pagination support is missing.


Caching
-------

* We do not return cached responses.


Limits
------

 * Limits support is missing.


Efficient Polling with the Changes-Since Parameter
--------------------------------------------------

* Effectively limit support of the changes-since parameter in **List Servers**
and **List Images**.
* Assume that garbage collection of deleted servers will only affect servers
  deleted ``POLL_TIME`` seconds in the past or earlier. Else loose the
  information of a server getting deleted.
* Images do not support a deleted state, so deletions cannot be tracked.


Versions
--------

* Version MIME type support is missing.
* Versionless requests are not supported.
* We hardcode the ``updated`` field in versions list
* Deployment note: The Atom metadata needs to be fixed


Extensions
----------

* Extensions support is missing.


Faults
------


API Operations
==============

Servers
-------

* ``hostId`` is always empty.
* ``affinityId`` is not returned.
* ``progress`` is always returned.
* ``self`` and ``bookmark`` atom links are not returned.
* **Get Server Details** will also return servers with a DELETED state.
* **Create Server** does not support setting the password in the request.

List Servers
............

=================== ====== ======== ==========
URI                 Method Cyclades OS Compute
=================== ====== ======== ==========
``/servers``        GET    ✔        ✔
``/servers/detail``
=================== ====== ======== ==========

* Both requests return a list of servers. The first returns just ``id`` and
``name``, while the second returns the full set of server attributes.

================= =================================== ======== ==========
Request Parameter Value                               Cyclades OS Compute
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

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
304 (No servers since date) Can be returned if ``changes-since`` is given
400 (Bad Request)           Invalid or malformed ``changes-since`` parameter
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
500 (Internal Server Error) The request cannot be completed because of an
internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================


The response data format is a list of servers under the ``servers`` label. A
server may have the fields presented bellow:

================= ====================== ======== ==========
Server Attributes Description            Cyclades OS Compute
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

* **hostId** is not used in Cyclades, but is returned as an empty string for compatibility


* **progress** is changing while the server is building up and has values
between 0 and 100. When it reaches 100 the server is built.


* **status** refers to `the status <#status-ref>`_ of the server

* **metadata** are custom key:value pairs used to specify various attributes of
the VM (e.g. OS, super user, etc.)


* **attachments** in Cyclades are lists of network interfaces (nics).
**Attachments** are different to OS Compute's **addresses**. The former is a
list of the server's `network interface connections <#nic-ref>`_ while the
later is just a list of networks. Thus, a Cyclades virtual server may be
connected to the same network through more than one distinct network interfaces
(e.g. server 43 is connected to network 101 with nic-43-1 and nic-43-2 in the
example bellow).

* **Network Interfaces (NICs)** contain information about a server's connection
to a network. Each nic is identified by an id of the form
nic-<server-id>-<ordinal-number> and may contain a ``network_id``, a
``mac_address``, ``ipv4`` and ``ipv6`` addresses and the ``firewallProfile`` of
the connection.

**Example List Servers: JSON**

.. code-block:: javascript

  {
      'servers':
          {'values': [
              {
                  'attachments': {'values': [
                          {
                              'id': 'nic-42-0',
                              'network_id': '101',
                              'mac_address': 'aa:00:00:49:2e:7e',
                              'firewallProfile': DISABLED,
                              'ipv4': '192.168.4.5',
                              'ipv6': '2001:648:2ffc:1222:a800:ff:fef5:3f5b'
                          }
                  ]},
                  'created': '2011-04-19T10:18:52.085737+00:00',
                  'flavorRef': 1,
                  'hostId': '',
                  'id': 42,
                  'imageRef': 3,
                  'metadata': {'values': {'foo': 'bar'}},
                  'name': 'My Server',
                  'status': 'ACTIVE',
                  'updated': u'2011-05-29T14:07:07.037602+00:00'
              },
              {
                  'attachments': {'values': [
                          {
                              'id': 'nic-43-0',
                              'mac': 'aa:00:00:91:2f:df',
                              'network_id': '1',
                              'ipv4': '192.168.32.2'
                          },
                          {
                              'id': 'nic-43-1',
                              'network_id': '101',
                              'mac_address': 'aa:00:00:49:2g:7f',
                              'firewallProfile': DISABLED,
                              'ipv4': '192.168.32.6',
                              'ipv6': '2001:648:2ffc:1222:a800:ff:fef5:3f5c'
                          },
                          {
                              'id': 'nic-43-2',
                              'network_id': '101',
                              'mac_address': 'aa:00:00:51:2h:7f',
                              'firewallProfile': DISABLED,
                              'ipv4': '192.168.32.7',
                              'ipv6': '2001:638:2eec:1222:a800:ff:fef5:3f5c'
                          }
                  ]},
                  'created': '2011-05-02T20:51:08.527759+00:00',
                  'flavorRef': 1,
                  'hostId': '',
                  'id': 43,
                  'imageRef': 3,
                  'name': 'Other Server',
                  'description': 'A sample server to showcase server requests',
                  'progress': 0,
                  'status': 'ACTIVE',
                  'updated': '2011-05-29T14:59:11.267087+00:00'
              }
          ]
      }
  }


Create Server
.............

=================== ====== ======== ==========
URI                 Method Cyclades OS Compute
=================== ====== ======== ==========
``/servers``        POST   ✔        ✔
=================== ====== ======== ==========

|

================= ===============
Request Parameter Value          
================= ===============
json              Respond in json
xml               Respond in xml 
================= ===============

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

The request body is json formated. It consists of a ``server`` tag over the
following attributes:

=========== ==================== ======== ==========
Name        Description          Cyclades OS Compute
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

* **metadata** are key:value pairs of custom server-specific metadata. There
are no semantic limitations.

* **personality** (optional) is a list of personality injections. A personality injection is a small set of changes to a virtual server. Each change modifies a
file on the virtual server, by injecting some data in it. The injected data
(``content``) should exceed 10240 *bytes* in size and must be base64 encoded. A personality injection contains the following attributes:

======== =================== ======== ==========
Name     Description         Cyclades OS Compute
======== =================== ======== ==========
path     File path on server ✔        ✔
contents Data to inject      ✔        ✔
group    User group          ✔        **✘**
mode     File access mode    ✔        **✘**
owner    File owner          ✔        **✘**
======== =================== ======== ==========

|

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
internal error
503 (Service Unavailable)   No available backends or service currently
unavailable
=========================== =====================

|

In case of a 200 return code, the Response Data are json-formated and consist
of a `list of attributes <#server-ref>`_ under the ``server`` tag:

For example::

  {"server": {
    "id": 28130
    "status": "BUILD",
    "updated": "2013-04-10T13:52:18.140686+00:00",
    "hostId": "",
    "name": "My Server Name: Example Name",
    "imageRef": "da7a211f-1db5-444a-938b-f901ce81a3e6",
    "created": "2013-04-10T13:52:17.085402+00:00",
    "flavorRef": 289,
    "adminPass": "fKCqlZe2at",
    "suspended": false,
    "progress": 0,
  }}

Get Server Stats
................

This operation returns URLs to graphs showing CPU and Network statistics. A
``refresh`` attribute is returned as well that is the recommended refresh rate
of the stats for the clients. This operation is no longer documented in OS
Compute v2.

============================== ====== ======== ==========
URI                            Method Cyclades OS Compute
============================== ====== ======== ==========
``/servers/<server-id>/stats`` GET    ✔        **✘**
============================== ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  =========================
Request Header  Value                    
==============  =========================
X-Auth-Token    User authentication token
==============  =========================

|

================= ===============
Request Parameter Value          
================= ===============
json              Respond in json
xml               Respond in xml 
================= ===============

* **json** and **xml** parameters are mutually exclusive. If none supported,
the response will be formated in json.

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Invalid server ID or Server deleted
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Server not found
500 (Internal Server Error) The request cannot be completed because of an
internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

|

================== ======================
Response Parameter Description           
================== ======================
serverRef          Server ID
refresh            Refresh frequency
cpuBar             Latest CPU load graph URL
cpuTimeSeries      CPU load / time graph URL
netBar             Latest Network load graph URL
netTimeSeries      Network load / time graph URL
================== ======================

**Example Get Server Stats Response: JSON**:

.. code-block:: javascript

  {
      "stats": {
          "serverRef": 1,
          "refresh": 60,
          "cpuBar": "http://stats.okeanos.grnet.gr/b9a1c3ca7e3b9fce75112c43565fb9960b16048c/cpu-bar.png",
          "cpuTimeSeries": "http://stats.okeanos.grnet.gr/b9a1c3ca7e3b9fce75112c43565fb9960b16048c/cpu-ts.png",
          "netBar": "http://stats.okeanos.grnet.gr/b9a1c3ca7e3b9fce75112c43565fb9960b16048c/net-bar.png",
          "netTimeSeries": "http://stats.okeanos.grnet.gr/b9a1c3ca7e3b9fce75112c43565fb9960b16048c/net-ts.png"
      }
  }

**Example Get Network Details Response: XML**:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <stats xmlns="http://docs.openstack.org/compute/api/v1.1"\
        xmlns:atom="http://www.w3.org/2005/Atom"
      serverRef="1"
      refresh="60"
      cpuBar="http://stats.okeanos.grnet.gr/b9a1x0b16048c/cpu-bar.png"
      cpuTimeSeries="http://stats.okeanos.grnet.gr/b9a1c3ca7e3b9fce75112c43565fb9960b16048c/cpu-ts.png"
      netBar="http://stats.okeanos.grnet.gr/b9a1x0b16048c/net-bar.png"
      netTimeSeries="http://stats.okeanos.grnet.gr/b9a1x0b16048c/net-ts.png">
  </stats>

Get Server Details
..................

======================== ====== ======== ==========
URI                      Method Cyclades OS Compute
======================== ====== ======== ==========
``/servers/<server id>`` GET    ✔        ✔
======================== ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed server id
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Server not found
500 (Internal Server Error) The request cannot be completed because of an
internal error
503 (Service Unavailable)   No available backends or service currently
unavailable
=========================== =====================

|

The response data format is a list of servers under the ``servers`` label. A
server may have the fields presented bellow:

================= ====================== ======== ==========
Server Attributes Description            Cyclades OS Compute
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

|

* **hostId** is not used in Cyclades, but is returned as an empty string for compatibility

* **progress** is changing while the server is building up and has values
between 0 and 100. When it reaches 100 the server is built.

* **status** refers to `the status <#status_ref>`_ of the server

* **metadata** are custom key:value pairs used to specify various attributes of
the VM (e.g. OS, super user, etc.)

* **attachments** in Cyclades are lists of network interfaces (NICs).
**Attachments** are different to OS Compute's **addresses**. The former is a
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

Rename Server
.............

======================== ====== ======== ==========
URI                      Method Cyclades OS Compute
======================== ====== ======== ==========
``/servers/<server id>`` PUT    ✔        ✔
======================== ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

The request body is json formated. It consists of a ``server`` tag over the
following attributes:

=========== ==================== ======== ==========
Name        Description          Cyclades OS Compute
=========== ==================== ======== ==========
name        The server name      ✔        ✔
accessIPv4  IP v4 address        **✘**    ✔
accessIPv6  IP v6 address        **✘**    ✔
=========== ==================== ======== ==========

* In Cyclades, a virtual server may use multiple network connections, instead
of limit them to one.

|

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
internal error
503 (Service Unavailable)   No available backends or service currently
unavailable
=========================== =====================

In case of a 204 return code, there will be no request results according to the
Cyclades API, while the new server details are returned according to OS Compute
API.

Delete Server
.............

======================== ====== ======== ==========
URI                      Method Cyclades OS Compute
======================== ====== ======== ==========
``/servers/<server id>`` DELETE ✔        ✔
======================== ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Malformed server id or machine already deleted
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Server not found
409 (Build In Progress)     Server is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
internal error
503 (Service Unavailable)   Action not supported or service currently
unavailable
=========================== =====================

Server Addresses
----------------

List Addresses
..............

List all network connections of a server

============================ ====== ======== ==========
URI                          Method Cyclades OS Compute
============================ ====== ======== ==========
``/servers/<server id>/ips`` GET    ✔        ✔
============================ ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS Compute
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

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed server id or machine already deleted
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Server not found
409 (Build In Progress)     Server is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
internal error
503 (Service Unavailable)   Service currently unavailable
=========================== =====================

If the return code is 200, the response body consists of a list of items under
the ``addresses`` tag. Each item refers to a network interface connection (NIC).

Each NIC connects the current server to a network. NICs are different to OS
Compute's addresses. The formers are the server's
`network interface connections <#nic-ref>`_ while the later describes a network. Cyclades API suggests this information can be acquired by the network_id, using
the network part of the API. Thus, a Cyclades virtual server may be connected
to the same network through more than one distinct network interfaces. The NIC
mechanism allows more metadata to describe the network and its relation to the
server.

**An example of a response, in JSON**

.. code-block:: javascript

  {
    "addresses": {
      "values": [
          {
            "network_id": "1",
            "mac_address": "aa:00:03:7a:84:bb",
            "firewallProfile": "DISABLED",
            "ipv4": "192.168.0.27",
            "ipv6": "2001:646:2ffc:1222:a820:3fd:fe7a:84bb",
            "id": "nic-25455-0"
          }, {
            "network_id": "7",
            "mac_address": "aa:00:03:7a:84:cc",
            "firewallProfile": "DISABLED",
            "ipv4": "192.168.0.28",
            "ipv6": "2002:646:2fec:1222:a820:3fd:fe7a:84bc",
            "id": "nic-25455-1"
          },
      ]
    }
  }

Get Server NIC by Network
.........................

Return the NIC that connects a server to a network

========================================= ====== ======== ==========
URI                                       Method Cyclades OS Compute
========================================= ====== ======== ==========
``/servers/<server id>/ips/<network id>`` GET    ✔        ✔
========================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server

* **network-id** is the identifier of the virtual server

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS Compute
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

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed server id or machine already deleted
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Server not found
409 (Build In Progress)     Server is not ready yet
500 (Internal Server Error) The request cannot be completed because of an
internal error
503 (Service Unavailable)   Service currently unavailable
=========================== =====================

If the return code is 200, the response body consists of a NIC under the
``network`` tag.

This NIC (`network interface connections <#nic-ref>`_) connects the specified
server to the specified network. NICs are only used in Cyclades API. The same
operation in OS Compute API returns a list of IP addresses.

**An example of a response, in JSON**

.. code-block:: javascript

  {
    "network": {
        "network_id": "7",
        "mac_address": "aa:00:03:7a:84:bb",
        "firewallProfile": "DISABLED",
        "ipv4": "192.168.0.27",
        "ipv6": "2001:646:2ffc:1222:a820:3fd:fe7a:84bb",
        "id": "nic-25455-0"
    }
  }

Server Actions
--------------

The request described in this section exists in both Synnefo API and OS Compute
API as a multi-operation request. The individual operations implemented through
this request are in many cases completely different between the two APIs.
Although this document focuses on Synnefo operations, differences and
similarities between the APIs are also briefed in this section.

|

============================= ======== ==========
Operations                    Cyclades OS Compute
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

|

====================================== ====== ======== ==========
URI                                    Method Cyclades OS Compute
====================================== ====== ======== ==========
``/servers/<server id>/action``        POST   ✔        ✔
====================================== ====== ======== ==========

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded (for console operation)
202 (OK)                    Request succeeded
400 (Bad Request)           Invalid request or unknown action
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
500 (Internal Server Error) The request cannot be completed because of an
internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Start server
................

This operation transitions a server from a STOPPED to an ACTIVE state.

Request body must contain a ``start`` tag on an empty directory::

  { 'start': {}}


Reboot Server
.............

This operation transitions a server from ``ACTIVE`` to ``REBOOT`` and then
``ACTIVE`` again. Synnefo and OS Compute APIs offer two reboot modes: soft and
hard. The only difference is that OS Compute distinguishes between the two
types of intermediate states (``REBOOT`` and ``HARD_REBOOT``) while rebooting,
but the expected behavior is the same in both APIs.

Request body must contain a ``reboot`` tag over a ``type`` tag on the reboot
type::

  { 'reboot' : { 'type': <reboot type>}}

* **reboot type** can be either ``SOFT`` or ``HARD``.

** Reboot Action Request Body Example: JSON **

.. code-block:: javascript
  
  {
    'reboot': {
      'type': 'hard'
      }
  }

Shutdown server
...............

This operation transitions a server from an ACTIVE to a STOPPED state.

Request body must contain a ``shutdown`` tag on an empty directory::

  { 'shutdown': {}}

Get Server Console
..................

The console operation arranges for an OOB console of the specified type. Only
consoles of type "vnc" are supported for now. Cyclades server uses a running
instance of vncauthproxy to setup proper VNC forwarding with a random password,
then returns the necessary VNC connection info to the caller.

Request body must a contain a ``console`` tag over a ``type`` tag on a console
type::

  console: {type: 'vnc' }

If successful, it returns a **200** code and also a json formated body with the
following fields:

================== ======================
Response Parameter Description           
================== ======================
host               The vncprocy host
port               vncprocy port
password           Temporary password
type               Connection type (only VNC)
================== ======================

|

**Example Action Console Response: JSON**:

.. code-block:: javascript

  {
      "console": {
          "type": "vnc",
          "host": "vm42.example.org",
          "port": 1234,
          "password": "513NR4PN0T"
      }
  }

**Example Action Console Response: XML**:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <console xmlns="http://docs.openstack.org/compute/api/v1.1"
      xmlns:atom="http://www.w3.org/2005/Atom"
      type="vnc"
      host="vm42.example.org"
      port="1234"
      password="513NR4PN0T">
  </console>

Set Firewall Profile
....................

The firewallProfile function sets a firewall profile for the public interface
of a server.

Request body must contain a ``firewallProfile`` tag over a ``profile`` tag on
the firewall type::

  firewallProfile: { profile: <firewall profile> }

* **firewall profile** can be ``ENABLED``, ``DISABLED`` or ``PROTECTED``

**Example Action firewallProfile: JSON**:

.. code-block:: javascript

  {
      "firewallProfile": {
          "profile": "ENABLED"
      }
  }


OS Compute API Specific
.......................

* `Change Administrator Password <http://docs.openstack.org/api/openstack-compute/2/content/Change_Password-d1e3234.html>`_
* `Rebuild Server <http://docs.openstack.org/api/openstack-compute/2/content/Rebuild_Server-d1e3538.html>`_
* `Resize Server <http://docs.openstack.org/api/openstack-compute/2/content/Resize_Server-d1e3707.html>`_
* `Confirm Resized Server <http://docs.openstack.org/api/openstack-compute/2/content/Confirm_Resized_Server-d1e3868.html>`_
* `Revert Resized Server <http://docs.openstack.org/api/openstack-compute/2/content/Revert_Resized_Server-d1e4024.html>`_
* `Create Image <http://docs.openstack.org/api/openstack-compute/2/content/Create_Image-d1e4655.html>`_


Server Metadata
---------------

List metadata
.............

.. note:: This operation is semantically equivalent in Cyclades and OS Compute.

================================= ====== ======== ==========
URI                               Method Cyclades OS Compute
================================= ====== ======== ==========
``/servers/<server-id>/meta``     GET    ✔        **✘**
``/servers/<server-id>/metadata`` GET    **✘**    ✔
================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server

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
400 (Bad Request)           Invalid server ID or Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Server not found
500 (Internal Server Error) The request cannot be completed because of an
internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

In case of a 200 response code, the response should contain a JSON encoded list
of key:value pairs, under a 'values' tag which lies under a ``metadata`` tag,
for example::

  { 
    'metadata': {
      'values': {
        'OS': 'Linux',
        'users': 'root'
      }
    }
  }

.. note:: In OS Compute API  the 'values' level is missing from the response

Set / Update Server Metadata
............................

In Cyclades API, setting new metadata and updating the values of existing ones
is achieved with the same type of request (POST), while in OS Compute API there
are two separate request types (PUT and POST for
`setting new <http://docs.openstack.org/api/openstack-compute/2/content/Create_or_Replace_Metadata-d1e5358.html>`_
and
`updating existing <http://docs.openstack.org/api/openstack-compute/2/content/Update_Metadata-d1e5208.html>`_
metadata, respectively).

In Cyclades API, metadata keys not referred by the operation will
remain intact, while metadata referred by the operation will be overwritten in
case of success.

================================= ====== ======== ==========
URI                               Method Cyclades OS Compute
================================= ====== ======== ==========
``/servers/<server-id>/meta``     POST    ✔        **✘**
``/servers/<server-id>/metadata`` PUT    **✘**    ✔
``/servers/<server-id>/metadata`` POST    **✘**   ✔
================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server

|

==============  =========================
Request Header  Value                    
==============  =========================
X-Auth-Token    User authentication token
==============  =========================

|

The request body should contain a JSON-formated set of key:value pairs, under
the ``metadata`` tag, e.g.::

  {'metadata': {'role': 'webmail', 'users': 'root,maild'}}

|

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
internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

|

In case of a 201 code, the response body should present the new state of
servers metadata. E.g.::

  {'metadata': {'OS': 'Linux', 'role': 'webmail', 'users': 'root,maild'}}

Get Metadata Item
.................

.. note:: This operation is semantically equivalent in Cyclades and OS Compute.

======================================= ====== ======== ==========
URI                                     Method Cyclades OS Compute
======================================= ====== ======== ==========
``/servers/<server-id>/meta/<key>``     GET    ✔        **✘**
``/servers/<server-id>/metadata/<key>`` GET    **✘**    ✔
======================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server
* **key** is the key of a matadatum key:value pair

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
400 (Bad Request)           Invalid server ID or Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Metadatum key not found
500 (Internal Server Error) The request cannot be completed because of an
internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

If the response code is 200, the response body contains the requested key:value
pair under a ``metadata`` tag. For example, if key was ``role``, the response
body would look similar to this::

  {'metadata': {'role': 'webmail'}}

.. note:: In OS Compute response, ``metadata`` is ``meta``

Set / Update Metadatum Item
...........................

.. note:: This operation is semantically equivalent in Cyclades and OS Compute.

======================================= ====== ======== ==========
URI                                     Method Cyclades OS Compute
======================================= ====== ======== ==========
``/servers/<server-id>/meta/<key>``     PUT    ✔        **✘**
``/servers/<server-id>/metadata/<key>`` PUT    **✘**    ✔
======================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server
* **key** is the key of a matadatum key:value pair

|

==============  =========================
Request Header  Value                    
==============  =========================
X-Auth-Token    User authentication token
==============  =========================

|

Request body should contain a ``key``:``value`` pair under a ``meta`` tag.
The ``value`` is the (new) value to set. The ``key`` of the metadatum may or
may not exist prior to the operation. For example, request with ``role`` as a
``key`` may contain the following request body::

  {'meta': {'role': 'gateway'}}

|

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
internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

|

If the response code is 201, the response body contains the ``key:pair``
that has just been created or updated, under a ``meta`` tag, so that the body
of the response is identical to the body of the request.

Delete Server metadata
......................

.. note:: This operation is semantically equivalent in Cyclades and OS Compute.

======================================= ====== ======== ==========
URI                                     Method Cyclades OS Compute
======================================= ====== ======== ==========
``/servers/<server-id>/meta/<key>``     DELETE ✔        **✘**
``/servers/<server-id>/metadata/<key>`` DELETE **✘**    ✔
======================================= ====== ======== ==========

* **server-id** is the identifier of the virtual server
* **key** is the key of a matadatum key:value pair

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
400 (Bad Request)           Invalid server ID
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Metadatum key not found
500 (Internal Server Error) The request cannot be completed because of an
internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Cyclades-specific Server Operations
-----------------------------------

The operations presented in this section are not included in OS Compute API.

Get Server Statistics
.....................

This operations is used to retrieve information about performance and network
usage of a server.

============================== ====== ======== ==========
URI                            Method Cyclades OS Compute
============================== ====== ======== ==========
``/servers/<server-id>/stats`` GET    ✔        **✘**
============================== ====== ======== ==========

* **server-id** is the identifier of the virtual server

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
400 (Bad Request)           Invalid server ID or Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Server not found
500 (Internal Server Error) The request cannot be completed because of an
internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

|

If the response code is 200, response body should container a set of
``key``:``value`` properties under the ``stats`` tag.

================ ============
Stats properties Description
================ ============
serverRef        The server id
refresh          Refresh frequency (seconds)
cpuBar           CPU load (last sampling)
cpuTimeSeries    CPU load graph for an 8h window
netBar           Network load (last sampling)
netTimeSeries    Network load graph for an 8h window
================ ============

For example:

.. code-block:: javascript

  {
    "stats": {
      "serverRef": 42,
      "refresh": 60,
      "cpuBar": "https://www.example.com/stats/snf-42/cpu-bar/",
      "netTimeSeries": "https://example.com/stats/snf-42/net-ts/",
      "netBar": "https://example.com/stats/snf-42/net-bar/",
      "cpuTimeSeries": "https://www.example.com/stats/snf-42/cpu-ts/"}
  }

Flavors
-------

* ``self`` and ``bookmark`` atom links are not returned.
* **List Flavors** returns just ``id`` and ``name`` if details is not requested.


Images
------

* ``progress`` is always returned.
* ``self`` and ``bookmark`` atom links are not returned.
* **List Images** returns just ``id`` and ``name`` if details are not requested.
* **List Images** can return 304 (even though not explicitly stated) when
  ``changes-since`` is given. 
* **List Images** does not return deleted images when ``changes-since`` is given.



Networks
--------

This is an extension to the OpenStack API.

A Server can connect to one or more networks identified by a numeric id. Each
user has access only to networks created by himself. When a network is deleted,
all connections to it are deleted. Likewise, when a server is deleted, all
connections of that server are deleted.

There is a special **public** network with the id *public* that can be accessed
at */networks/public*. All servers are connected to **public** by default and
this network can not be deleted or modified in any way.


List Networks
.............

**GET** /networks

**GET** /networks/detail

**Normal Response Codes**: 200, 203

**Error Response Codes**: computeFault (400, 500), serviceUnavailable (503),
unauthorized (401), badRequest (400), overLimit (413)

This operation provides a list of private networks associated with your account.

This operation does not require a request body.

**Example Networks List Response: JSON (detail)**:

.. code-block:: javascript

  {
      "networks": {
          "values": [
              {
                  "id": "public",
                  "name": "public",
                  "created": "2011-04-20T15:31:08.199640+00:00",
                  "updated": "2011-05-06T12:47:05.582679+00:00",
                  "servers": {
                      "values": [1, 2, 3]
                  }
              },
              {
                  "id": 2,
                  "name": "private",
                  "created": "2011-04-20T14:32:08.199640+00:00",
                  "updated": "2011-05-06T11:40:05.582679+00:00",
                  "servers": {
                      "values": [1]
                  }
              }
          ]
      }
  }

**Example Networks List Response: XML (detail)**:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <networks xmlns="http://docs.openstack.org/compute/api/v1.1" xmlns:atom="http://www.w3.org/2005/Atom">
    <network id="public" name="public" updated="2011-05-02T21:33:25.606672+00:00" created="2011-04-20T15:31:08.199640+00:00">
      <servers>
        <server id="1"></server>
        <server id="2"></server>
        <server id="3"></server>
      </servers>
    </network>
    <network id="2" name="private" updated="2011-05-06T12:47:05.582679+00:00" created="2011-04-20T15:31:33.911299+00:00">
      <servers>
        <server id="1"></server>
      </servers>
    </network>
  </networks>


Create Network
..............

**POST** /networks

**Normal Response Code**: 202

**Error Response Codes**: computeFault (400, 500), serviceUnavailable (503),
unauthorized (401), badMediaType(415), badRequest (400), overLimit (413)

This operation asynchronously provisions a new private network.

**Example Create Network Request: JSON**:

.. code-block:: javascript

  {
      "network": {
          "name": "private_net",
      }
  }

**Example Create Network Response: JSON**:

.. code-block:: javascript

  {
      "network": {
          "id": 3,
          "name": "private_net",
          "created": "2011-04-20T15:31:08.199640+00:00",
          "servers": {
              "values": []
          }
      }
  }

**Example Create Network Response: XML**:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <network xmlns="http://docs.openstack.org/compute/api/v1.1" xmlns:atom="http://www.w3.org/2005/Atom"
   id="2" name="foob" created="2011-04-20T15:31:08.199640+00:00">
    <servers>
    </servers>
  </network>


Get Network Details
...................

**GET** /networks/*id*

**Normal Response Codes**: 200, 203

**Error Response Codes**: computeFault (400, 500), serviceUnavailable (503),
unauthorized (401), badRequest (400), itemNotFound (404), overLimit (413)

This operation returns the details of a specific network by its id.

This operation does not require a request body.

**Example Get Network Details Response: JSON**:

.. code-block:: javascript

  {
      "network": {
          "id": 3,
          "name": "private_net",
          "servers": {
              "values": [1, 7]
          }
      }
  }

**Example Get Network Details Response: XML**::

  <?xml version="1.0" encoding="UTF-8"?>
  <network xmlns="http://docs.openstack.org/compute/api/v1.1" xmlns:atom="http://www.w3.org/2005/Atom"
   id="2" name="foob" updated="2011-05-02T21:33:25.606672+00:00" created="2011-04-20T15:31:08.199640+00:00">
    <servers>
      <server id="1"></server>
      <server id="7"></server>
    </servers>
  </network>


Update Network Name
...................

**PUT** /networks/*id*

**Normal Response Code**: 204

**Error Response Codes**: computeFault (400, 500), serviceUnavailable (503),
unauthorized (401), badRequest (400), badMediaType(415), itemNotFound (404),
overLimit (413) 

This operation changes the name of the network in the Compute system.

**Example Update Network Name Request: JSON**:

.. code-block:: javascript

  {
      "network": {
          "name": "new_name"
      }
  }

This operation does not contain a response body.


Delete Network
..............

**DELETE** /networks/*id*

**Normal Response Code**: 204

**Error Response Codes**: computeFault (400, 500), serviceUnavailable (503),
unauthorized (401), itemNotFound (404), unauthorized (401), overLimit (413) 

This operation deletes a network from the system.

This operation does not require a request or a response body.


Network Actions
---------------

Add Server
..........

**POST** /networks/*id*/action

**Normal Response Code**: 202

**Error Response Codes**: computeFault (400, 500), serviceUnavailable (503),
unauthorized (401), badRequest (400), badMediaType(415), itemNotFound (404),
overLimit (413)

This operation adds a server to the specified network.

**Example Action Add: JSON**:

.. code-block:: javascript

  {
      "add" : {
          "serverRef" : 42
      }
  }

This operation does not contain a response body.


Remove Server
.............

**POST** /networks/*id*/action

**Normal Response Code**: 202

**Error Response Codes**: computeFault (400, 500), serviceUnavailable (503),
unauthorized (401), badRequest (400), badMediaType(415), itemNotFound (404),
overLimit (413)

This operation removes a server from the specified network.

**Example Action Remove: JSON**:

.. code-block:: javascript

  {
      "remove" : {
          "serverRef" : 42
      }
  }

This operation does not contain a response body.

Index of details
----------------

.. _server-ref:

Server Attributes
.................

================ ========================== ======== ==========
Server attribute Description                Cyclades OS Compute
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
Status        Description          Cyclades OS Compute
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

.. _nic-ref:

Network Interface Connection (NIC)
..................................

A Network Interface Connection (NIC) represents a servers connection to a network.

A NIC is identified by a server and an (obviously unique) mac address. A server can have multiple NICs, though. In practice, a NIC id is used of reference and identification.

Each NIC is used to connect a specific server to a network. The network is aware of that connection for as long as it holds. If a NIC is disconnected from a network, it is destroyed.

A NIC specification contains the following information:

================= ====================== ======== ==========
Server Attributes Description            Cyclades OS Compute
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
