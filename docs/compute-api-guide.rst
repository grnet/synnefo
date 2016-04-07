.. _compute-api-guide:

API Guide
*********

`Cyclades <cyclades.html>`_ is the Compute Service of `Synnefo
<http://www.synnefo.org>`_. The Cyclades/Compute API complies with
`OpenStack Compute <http://docs.openstack.org/api/openstack-compute/2/content>`_
with custom extensions when needed.

This document's goals are:

* Define the Cyclades/Compute REST API
* Clarify the differences between Cyclades and OpenStack/Compute

Users and developers who wish to access Cyclades through its REST API are
advised to use the
`kamaki <http://www.synnefo.org/docs/kamaki/latest/index.html>`_ command-line
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
passed to the service, which is used to authenticate the user and retrieve user
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

* Version MIME type and versionless requests are not currently supported.

* Cyclades only supports JSON Requests and JSON/XML Responses. XML Requests are
  currently not supported.

* Optional content compression support is currently not supported.

* To prevent abuse, HTTP sessions have a timeout of 20 seconds before being
  closed.

* Full URI references and ``self`` and ``bookmark`` links are not supported.

* Pagination is currently not supported.

* Cached responses are currently not supported.

* Limits are currently not supported.


API Operations
==============

.. rubric:: Servers

================================================== ========================================= ====== ======== ==========
Description                                        URI                                       Method Cyclades OS/Compute
================================================== ========================================= ====== ======== ==========
`List <#list-servers>`_                            ``/servers``                              GET    ✔        ✔
\                                                  ``/servers/detail``                       GET    ✔        ✔
`Create <#create-server>`_                         ``/servers``                              POST   ✔        ✔
`Get Stats <#get-server-stats>`_                   ``/servers/<server-id>/stats``            GET    ✔        **✘**
`Get Diagnostics <#get-server-diagnostics>`_       ``/servers/<server-id>/diagnostics``      GET    ✔        **✘**
`Get Details <#get-server-details>`_               ``/servers/<server id>``                  GET    ✔        ✔
`Rename <#rename-server>`_                         ``/servers/<server id>``                  PUT    ✔        ✔
`Delete <#delete-server>`_                         ``/servers/<server id>``                  DELETE ✔        ✔
`List Connections <#list-server-connections>`_     ``/servers/<server id>/ips``              GET    ✔        ✔
`Get Connection <#connection-with-network>`_       ``/servers/<server id>/ips/<network id>`` GET    ✔        ✔
`List Metadata <#list-server-metadata>`_           ``/servers/<server-id>/metadata``         GET    ✔        ✔
`Update Metadata <#set-update-server-metadata>`_   ``/servers/<server-id>/metadata``         PUT    **✘**    ✔
\                                                  ``/servers/<server-id>/metadata``         POST   ✔        ✔
`Get Meta Item <#get-server-metadata-item>`_       ``/servers/<server-id>/metadata/<key>``   GET    ✔        ✔
`Update Meta Item <#update-server-metadata-item>`_ ``/servers/<server-id>/metadata/<key>``   PUT    ✔        ✔
`Delete Meta Item <#delete-server-metadata>`_      ``/servers/<server-id>/metadata/<key>``   DELETE ✔        ✔
`Actions <#server-actions>`_                       ``/servers/<server id>/action``           POST   ✔        ✔
================================================== ========================================= ====== ======== ==========

.. rubric:: Flavors

==================================== ======================== ====== ======== ==========
Description                          URI                      Method Cyclades OS/Compute
==================================== ======================== ====== ======== ==========
`List <#list-flavors>`_              ``/flavors``             GET    ✔        ✔
\                                    ``/flavors/detail``      GET    ✔        **✘**
`Get details <#get-flavor-details>`_ ``/flavors/<flavor-id>`` GET    ✔        ✔
==================================== ======================== ====== ======== ==========

.. rubric:: Images

=========================================== ===================================== ====== ======== ==========
Description                                 URI                                   Method Cyclades OS/Compute
=========================================== ===================================== ====== ======== ==========
`List <#list-images>`_                      ``/images``                           GET    ✔        ✔
\                                           ``/images/detail``                    GET    ✔        ✔
`Get details <#get-image-details>`_         ``/images/<image-id>``                GET    ✔        ✔
`Delete <#delete-image>`_                   ``/images/<image id>``                DELETE ✔        ✔
`List Metadata <#list-image-metadata>`_     ``/images/<image-id>/metadata``       GET    ✔        ✔
`Update Metadata <#update-image-metadata>`_ ``/images/<image-id>/metadata``       POST   ✔        ✔
\                                           ``/images/<image-id>/metadata``       PUT    **✘**    ✔
`Get Meta Item <#get-image-metadata>`_      ``/image/<image-id>/metadata/<key>``  GET    ✔        ✔
`Update Metadata <#update-image-metadata>`_ ``/images/<image-id>/metadata/<key>`` PUT    ✔        ✔
`Delete Metadata <#delete-image-metadata>`_ ``/images/<image-id>/metadata/<key>`` DELETE ✔        ✔
=========================================== ===================================== ====== ======== ==========

List Servers
------------

List all virtual servers owned by the user.

.. rubric:: Request

=================== ====== ======== ==========
URI                 Method Cyclades OS/Compute
=================== ====== ======== ==========
``/servers``        GET    ✔        ✔
``/servers/detail`` GET    ✔        ✔
=================== ====== ======== ==========

* Both requests return a list of servers. The first returns just ``id``,
  ``name`` and ``links``, while the second returns the full collections of
  server attributes.

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

The server attributes are listed `here <#server-ref>`_

*Example List Servers: JSON (regular)*

.. code-block:: javascript

  GET https://example.org/compute/v2.0/servers


  {
    "servers": [
      {
        "links": [
          {
            "href": "https://example.org/compute/v2.0/servers/42", 
            "rel": "self"
          }, {
            "href": "https://example.org/compute/v2.0/servers/42", 
            "rel": "bookmark"
          }
        ],
        "id": "42",
        "name": "My Server",
      }, {
        "links": [
          {
            "href": "https://example.org/compute/v2.0/servers/43", 
            "rel": "self"
          }, {
            "href": "https://example.org/compute/v2.0/servers/43", 
            "rel": "bookmark"
          }
        ],
        "id": "84",
        "name": "My Server",
      }
    ]
  }

*Example List Servers: JSON (detail)*

  GET https://example.org/compute/v2.0/servers/detail


.. code-block:: javascript

  {
    "servers": [
      {
        "addresses": [
          "2718": [
            {
              "version": 6,
              "addr": "2001:443:2dfc:1232:a810:3cf:fe9b:21ab",
              "OS-EXT-IPS:type": "fixed"
            }
          ],
          "2719": [
            {
              "version": 4,
              "addr": "192.168.1.2",
              "OS-EXT-IPS:type": "floating"
            }
          ]
        ],
        "attachments": [
            {
              "id": "18",
              "network_id": "2718",
              "mac_address": "aa:01:02:6c:34:ab",
              "firewallProfile": "DISABLED",
              "ipv4": "",
              "ipv6": "2001:443:2dfc:1232:a810:3cf:fe9b:21ab"
              "OS-EXT-IPS:type": "fixed"
            }, {
              "id": "19",
              "network_id": "2719",
              "mac_address": "aa:00:0c:6d:34:bb",
              "firewallProfile": "PROTECTED",
              "ipv4": "192.168.1.2",
              "ipv6": ""
              "OS-EXT-IPS:type": "floating"
            }
        ],
        "links": [
          {
            "href": "https://example.org/compute/v2.0/servers/42", 
            "rel": "self"
          }, {
            "href": "https://example.org/compute/v2.0/servers/42", 
            "rel": "bookmark"
          }
        ],
        "image": {
          "id": "im4g3-1d",
          "links": [
            {
              "href": "https://example.org/compute/v2.0/images/im4g3-1d", 
              "rel": "self"
            }, {
              "href": "https://example.org/compute/v2.0/images/im4g3-1d", 
              "rel": "bookmark"
            }, {
              "href": "https://example.org/image/v1.0/images/im4g3-1d", 
              "rel": "alternate"
            }
          ]
        },
        "suspended": false,
        "created': '2011-04-19T10:18:52.085737+00:00',
        "flavor": {
          "id": 1",
          "links": [
            {
              "href": "https://example.org/compute/v2.0/flavors/1", 
              "rel": "self"
            }, {
              "href": "https://example.org/compute/v2.0/flavors/1", 
              "rel": "bookmark"
            }
          ]
        },
        "id": "42",
        "security_groups": [{"name": "default"}],
        "user_id": "s0m5-u5e7-1d",
        "accessIPv4": "",
        "accessIPv6": "",
        "progress": 100,
        "config_drive": "",
        "status": "ACTIVE",
        "updated": "2011-05-29T14:07:07.037602+00:00",
        "hostId": "",
        "SNF:fqdn": "snf-42.vm.example.org",
        "key_name": null,
        "name": "My Server",
        "created": "2014-02-12T08:31:37.834542+00:00",
        "tenant_id": "s0m5-u5e7-1d",
        "SNF:port_forwarding": {},
        "SNF:task_state": "",
        "diagnostics": [
            {
                "level": "DEBUG",
                "created": "2014-02-12T08:31:37.834542+00:00",
                "source": "image-info",
                "source_date": "2014-02-12T08:32:35.929507+00:00",
                "message": "Image customization finished successfully.",
                "details": null
            }
        ],
        "metadata": {
            "os": "debian",
            "users": "root"
        }
      }, {
      {
        "addresses": [
          "2718": [
            {
              "version": 6,
              "addr": "2001:443:2dfc:1232:a810:3cf:fe9b:21cd",
              "OS-EXT-IPS:type": "fixed"
            }
          ],
          "4178": [
            {
              "version": 4,
              "addr": "192.168.1.3",
              "OS-EXT-IPS:type": "floating"
            }
          ]
        ],
        "attachments": [
            {
              "id": "36",
              "network_id": "2718",
              "mac_address": "aa:01:02:6c:34:cd",
              "firewallProfile": "DISABLED",
              "ipv4": "",
              "ipv6": "2001:443:2dfc:1232:a810:3cf:fe9b:21cd"
              "OS-EXT-IPS:type": "fixed"
            }, {
              "id": "38",
              "network_id": "4178",
              "mac_address": "aa:00:0c:6d:34:cc",
              "firewallProfile": "PROTECTED",
              "ipv4": "192.168.1.3",
              "ipv6": ""
              "OS-EXT-IPS:type": "floating"
            }
        ],
        "links": [
          {
            "href": "https://example.org/compute/v2.0/servers/84", 
            "rel": "self"
          }, {
            "href": "https://example.org/compute/v2.0/servers/84", 
            "rel": "bookmark"
          }
        ],
        "image": {
          "id": "im4g3-1d",
          "links": [
            {
              "href": "https://example.org/compute/v2.0/images/im4g3-1d", 
              "rel": "self"
            }, {
              "href": "https://example.org/compute/v2.0/images/im4g3-1d", 
              "rel": "bookmark"
            }, {
              "href": "https://example.org/image/v1.0/images/im4g3-1d", 
              "rel": "alternate"
            }
          ]
        },
        "suspended": false,
        "created': '2011-04-21T10:18:52.085737+00:00',
        "flavor": {
          "id": 3",
          "links": [
            {
              "href": "https://example.org/compute/v2.0/flavors/3", 
              "rel": "self"
            }, {
              "href": "https://example.org/compute/v2.0/flavors/3", 
              "rel": "bookmark"
            }
          ]
        },
        "id": "84",
        "security_groups": [{"name": "default"}],
        "user_id": "s0m5-u5e7-1d",
        "accessIPv4": "",
        "accessIPv6": "",
        "progress": 100,
        "config_drive": "",
        "status": "ACTIVE",
        "updated": "2011-05-30T14:07:07.037602+00:00",
        "hostId": "",
        "SNF:fqdn": "snf-84.vm.example.org",
        "key_name": null,
        "name": "My Other Server",
        "created": "2014-02-21T08:31:37.834542+00:00",
        "tenant_id": "s0m5-u5e7-1d",
        "SNF:port_forwarding": {},
        "SNF:task_state": "",
        "diagnostics": [
          {
            "level": "DEBUG",
            "created": "2014-02-21T08:31:37.834542+00:00",
            "source": "image-info",
            "source_date": "2014-02-21T08:32:35.929507+00:00",
            "message": "Image customization finished successfully.",
            "details": null
          }
        ],
        "metadata": {
          "os": "debian",
          "users": "root"
        }
      }
    ]
  }


Create Server
-------------

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
        ...
      ],
      networks: [
        ...
      ]
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
project     Project assignment   ✔        **✘**
=========== ==================== ======== ==========

* **name** can be any string

* **imageRef** and **flavorRef** should refer to existing images and hardware
  flavors accessible by the user

* **metadata** are ``key``:``value`` pairs of custom server-specific metadata.
  There are no semantic limitations, although the ``OS`` and ``USERS`` values
  should rather be defined

* **project** (optional) is the project where the VM is to be assigned. If not
  given, user's system project is assumed (identified with the same uuid as the
  user).

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

* **personality** (optional) is a list of
  `personality injections <#personality-ref>`_

* **networks** (optional) is a list of
  `network connections <#network-on-vm-ref>`_.

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request data
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             User is not allowed to perform this operation
404 (Not Found)             Image or Flavor not found
413 (Over Limit)            Exceeded some resource limit
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

.. note:: The ``adminPass`` attribute is generated in the response. This is the
    only case where this attribute appears in a response.

*Example Create Server Response: JSON*

.. code-block:: javascript

  POST https://example.org/compute/v2.0/servers


  {
    "server": {
      "name": "My Example Server",
      "id": 5678,
      "status": "BUILD",
      "created": "2013-04-10T13:52:17.085402+00:00",
      "updated": "2013-04-10T13:52:17.085402+00:00",
      "adminPass": "fKCqlZe2at",
      "progress": 0
      "metadata": {
        "OS": "debian",
        "USERS": "root"
      },
      ...
    }
  }

.. _personality-ref:

Personality: injecting files while creating a virtual server
............................................................

The term "personality" refers to a mechanism for injecting data as files into
the file system of a virtual server while the server is being created. This
mechanism has many application e.g., the injection of ``ssh keys`` for secure
password-less access, automation in user profile configuration, etc.

A personality injection contains the following attributes:

====================== =================== ======== ==========
Personality Attributes Description         Cyclades OS/Compute
====================== =================== ======== ==========
path                   File path on server ✔        ✔
contents               Data to inject      ✔        ✔
group                  User group          ✔        **✘**
mode                   File access mode    ✔        **✘**
owner                  File owner          ✔        **✘**
====================== =================== ======== ==========

* **path** is the path (including name) for the file on the remote server. If
  the file does not exist, it will be created
* **contents** is the data to be injected, must not exceed 10240 *bytes* and
  must be base64-encoded
* **mode** is the access mode of the created remote file and must be a number
  (usually octal or decimal)

*Example Create Server Request: JSON*

.. code-block:: javascript

  POST https://example.org/compute/v2.0/servers
  {
    "server": {
      "name": "My Password-less Server",
      "personality": [
        {
          "path": "/home/someuser/.ssh/authorized_keys",
          "contents": "Some users public key",
          "group": "users",
          "mode": 0600,
          "owner": "someuser"
        }, {
          "path": "/home/someuser/.bashrc",
          "contents": "bash configuration",
          "group": "users",
          "mode": 0777,
          "owner": "someuser"
        }
      ],
      ...
    }
  }

.. _network-on-vm-ref:

Network connections on virtual server creation
..............................................

A network connection is established by creating a port that connects a virtual
device with a network. There are five cases:

* The ``network`` attribute is not provided. In that case, the service will
  apply its default policy (e.g., automatic public network and IP assignment)
* The ``network`` attribute is an empty list. In that case, the virtual server
  will not have any network connections
* Provide an existing network ID. In that case, the virtual server will be
  connected to that network.
* Provide an existing network ID and an IP (which is already associated to that
  network). In that case, the virtual server will be connected to that network
  with this specific IP attached.
* Provide an existing port ID to establish a connection through it.

========================================= ======== ==========
Network attributes on server construction Cyclades OS/Compute
========================================= ======== ==========
uuid                                      ✔        ✔
fixed_ip                                  ✔        ✔
port                                      ✔        ✔
========================================= ======== ==========

E.g., the following example connects a public network with an IP (2719) and a
private network (9876) on the virtual server under construction:

* Example Connect server on various networks*

.. code-block:: python

  POST https://example.org/compute/v2.0/servers
  {
    "server": {
      "networks": [
        {"uuid": 9876},
        {"uuid": 2719, "fixed_ip": "192.168.1.2"},
      ],
      ...
    }
  }


Get Server Stats
----------------

.. note:: This operation is not part of OS/Compute v2.

This operation returns URLs of graphs showing CPU and Network statistics.

.. rubric:: Request

============================== ====== ======== ==========
URI                            Method Cyclades OS/Compute
============================== ====== ======== ==========
``/servers/<server-id>/stats`` GET    ✔        **✘**
============================== ====== ======== ==========

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

  GET https://example.org/compute/v2.0/servers/5678/stats
  {
    "stats": {
      "serverRef": 5678,
      "refresh": 60,
      "cpuBar": "http://stats.okeanos.grnet.gr/b9a...048c/cpu-bar.png",
      "cpuTimeSeries": "http://stats.okeanos.grnet.gr/b9a...048c/cpu-ts.png",
      "netBar": "http://stats.okeanos.grnet.gr/b9a...048c/net-bar.png",
      "netTimeSeries": "http://stats.okeanos.grnet.gr/b9a...048c/net-ts.png"
    }
  }

Get Server Diagnostics
----------------------

.. note:: This operation is not part of OS/Compute v2.

This operation returns diagnostic information (logs) for a server.

.. rubric:: Request

==================================== ====== ======== ==========
URI                                  Method Cyclades OS/Compute
==================================== ====== ======== ==========
``/servers/<server-id>/diagnostics`` GET    ✔        **✘**
==================================== ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

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

  GET https://example.org/compute/v2.0/servers/5678/diagnostics
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
    }
  ]

Get Server Details
------------------

This operation returns detailed information for a virtual server

.. rubric:: Request

======================== ====== ======== ==========
URI                      Method Cyclades OS/Compute
======================== ====== ======== ==========
``/servers/<server id>`` GET    ✔        ✔
======================== ====== ======== ==========

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

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

Server attributes are explained `here <#server-ref>`_

*Example get server Details*

.. code-block:: javascript

  GET https://example.org/compute/v2.0/servers/84


  {
    "server": {
      "addresses": [
        "2718": [
          {
            "version": 6,
            "addr": "2001:443:2dfc:1232:a810:3cf:fe9b:21cd",
            "OS-EXT-IPS:type": "fixed"
          }
        ],
        "4178": [
          {
            "version": 4,
            "addr": "192.168.1.3",
            "OS-EXT-IPS:type": "floating"
          }
        ]
      ],
      "attachments": [
          {
            "id": "36",
            "network_id": "2718",
            "mac_address": "aa:01:02:6c:34:cd",
            "firewallProfile": "DISABLED",
            "ipv4": "",
            "ipv6": "2001:443:2dfc:1232:a810:3cf:fe9b:21cd"
            "OS-EXT-IPS:type": "fixed"
          }, {
            "id": "38",
            "network_id": "4178",
            "mac_address": "aa:00:0c:6d:34:cc",
            "firewallProfile": "PROTECTED",
            "ipv4": "192.168.1.3",
            "ipv6": ""
            "OS-EXT-IPS:type": "floating"
          }
      ],
      "links": [
        {
          "href": "https://example.org/compute/v2.0/servers/84", 
          "rel": "self"
        }, {
          "href": "https://example.org/compute/v2.0/servers/84", 
          "rel": "bookmark"
        }
      ],
      "image": {
        "id": "im4g3-1d",
        "links": [
          {
            "href": "https://example.org/compute/v2.0/images/im4g3-1d", 
            "rel": "self"
          }, {
            "href": "https://example.org/compute/v2.0/images/im4g3-1d", 
            "rel": "bookmark"
          }, {
            "href": "https://example.org/image/v1.0/images/im4g3-1d", 
            "rel": "alternate"
          }
        ]
      },
      "suspended": false,
      "created': '2011-04-21T10:18:52.085737+00:00',
      "flavor": {
        "id": 3",
        "links": [
          {
            "href": "https://example.org/compute/v2.0/flavors/3", 
            "rel": "self"
          }, {
            "href": "https://example.org/compute/v2.0/flavors/3", 
            "rel": "bookmark"
          }
        ]
      },
      "id": "84",
      "security_groups": [{"name": "default"}],
      "user_id": "s0m5-u5e7-1d",
      "accessIPv4": "",
      "accessIPv6": "",
      "progress": 100,
      "config_drive": "",
      "status": "ACTIVE",
      "updated": "2011-05-30T14:07:07.037602+00:00",
      "hostId": "",
      "SNF:fqdn": "snf-84.vm.example.org",
      "key_name": null,
      "name": "My Other Server",
      "created": "2014-02-21T08:31:37.834542+00:00",
      "tenant_id": "s0m5-u5e7-1d",
      "SNF:port_forwarding": {},
      "SNF:task_state": "",
      "diagnostics": [
        {
          "level": "DEBUG",
          "created": "2014-02-21T08:31:37.834542+00:00",
          "source": "image-info",
          "source_date": "2014-02-21T08:32:35.929507+00:00",
          "message": "Image customization finished successfully.",
          "details": null
        }
      ],
      "metadata": {
        "os": "debian",
        "users": "root"
      }
    }
  }

Rename Server
-------------

In Synnefo/Cyclades, only the ``name`` attribute of a virtual server can be
modified with this call.

.. rubric:: Response

======================== ====== ======== ==========
URI                      Method Cyclades OS/Compute
======================== ====== ======== ==========
``/servers/<server id>`` PUT    ✔        ✔
======================== ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

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

* **accessIPv4** and **accessIPv6** are ignored. Cyclades features a different
  `mechanism for managing network connections <network-api-guide.html>`_ on
  servers

*Example Rename Server Request: JSON*

.. code-block:: javascript

  {"server": {"name": "New name"}}

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
-------------

Delete a virtual server. When a server is deleted, all its attachments (ports)
are deleted as well.

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

List Server Connections
-----------------------

List a server's network connections. In Cyclades, connections are ports between
a network and the server.

.. rubric:: Request

============================ ====== ======== ==========
URI                          Method Cyclades OS/Compute
============================ ====== ======== ==========
``/servers/<server id>/ips`` GET    ✔        ✔
============================ ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

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
    <network id>: [
      {
        version: <4 or 6>,
        addr: <IP address, if any>
        OS-EXT-TYPE:type: <floating or fixed>
      },
      ...
    ],
    ...
  ],
  attachments: [
    {
      <attachment attribute>: ...,
      ...
    },
    ...
  ]

Attachment attributes are explained `here <#attachments-ref>`_

*Example List Addresses: JSON*

.. code-block:: javascript

  GET https://example.org/compute/v2.0/servers/84/ips/

  {
      "addresses": [
        "2718": [
          {
            "version": 6,
            "addr": "2001:443:2dfc:1232:a810:3cf:fe9b:21cd",
            "OS-EXT-IPS:type": "fixed"
          }
        ],
        "4178": [
          {
            "version": 4,
            "addr": "192.168.1.3",
            "OS-EXT-IPS:type": "floating"
          }
        ]
      ],
      "attachments": [
          {
            "id": "36",
            "network_id": "2718",
            "mac_address": "aa:01:02:6c:34:cd",
            "firewallProfile": "DISABLED",
            "ipv4": "",
            "ipv6": "2001:443:2dfc:1232:a810:3cf:fe9b:21cd"
            "OS-EXT-IPS:type": "fixed"
          }, {
            "id": "38",
            "network_id": "4178",
            "mac_address": "aa:00:0c:6d:34:cc",
            "firewallProfile": "PROTECTED",
            "ipv4": "192.168.1.3",
            "ipv6": ""
            "OS-EXT-IPS:type": "floating"
          }
      ]
  }

Connection with network
-----------------------

Get information on a network connected on a server

.. rubric:: Request

========================================= ====== ======== ==========
URI                                       Method Cyclades OS/Compute
========================================= ====== ======== ==========
``/servers/<server id>/ips/<network id>`` GET    ✔        ✔
========================================= ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

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
    <network id>: [
      {
        version: <4 or 6>,
        addr: <IP address, if any>
        OS-EXT-TYPE:type: <floating or fixed>
      },
  }

**Example**

.. code-block:: javascript

  GET https://example.org/compute/v2.0/servers/84/ips/2718


  "network": {
    "2718": [
      {
        "version": 6,
        "addr": "2001:443:2dfc:1232:a810:3cf:fe9b:21cd",
        "OS-EXT-IPS:type": "fixed"
      }
    ]
  }

List Server Metadata
--------------------

.. note:: This operation is semantically equivalent in Cyclades and OS/Compute
  besides the different URI.

.. rubric:: Request

================================= ====== ======== ==========
URI                               Method Cyclades OS/Compute
================================= ====== ======== ==========
``/servers/<server-id>/metadata`` GET    ✔        ✔
================================= ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

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

* Key is in uppercase by convention

*Example List Server Metadata: JSON*

.. code-block:: javascript

  {
    ""metadata": {
      "OS": "Linux",
      "USERS": "root"
    }
  }

Set / Update Server Metadata
----------------------------

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

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

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
------------------------

Get the value of a specific piece of metadata of a virtual server

.. rubric:: Request

======================================= ====== ======== ==========
URI                                     Method Cyclades OS/Compute
======================================= ====== ======== ==========
``/servers/<server-id>/metadata/<key>`` GET    ✔        ✔
======================================= ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Invalid server ID or Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Meta key not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Response body content::

  metadata: {<key>: <value>}

*Example Get Server Metadata for Item 'role', JSON*

.. code-block:: javascript

  {"metadata": {"role": "webmail"}}

Update Server Metadata Item
---------------------------

Set a new or update an existing a metadum value for a virtual server.

.. rubric:: Request

======================================= ====== ======== ==========
URI                                     Method Cyclades OS/Compute
======================================= ====== ======== ==========
``/servers/<server-id>/metadata/<key>`` PUT    ✔        ✔
======================================= ====== ======== ==========

|

==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

Request body content::

  metadata: {<key>: <value>}

*Example Request to Set or Update Server Metadata "role": JSON*

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
404 (Not Found)             Meta key not found
413 (OverLimit)             Maximum number of metadata exceeded
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== ====================

Response body content::

  metadata: {<key>: <value>}

*Example Set or Update Server Metadata "role":"gateway": JSON*

.. code-block:: javascript

  {"metadata": {"role": "gateway"}}

Delete Server Metadata
----------------------

Delete a metadata of a virtual server

.. rubric:: Request

======================================= ====== ======== ==========
URI                                     Method Cyclades OS/Compute
======================================= ====== ======== ==========
``/servers/<server-id>/metadata/<key>`` DELETE ✔        ✔
======================================= ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Invalid server ID
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Administratively suspended server
404 (Not Found)             Metadata key not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

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
`Reassign <#reassign-server>`_                  ✔        **✘**
`Change Admin Password <#os-compute-specific>`_ **✘**    ✔
`Rebuild <#os-compute-specific>`_               **✘**    ✔
`Resize <#resize-server>`_                      ✔        ✔
`Confirm Resized <#os-compute-specific>`_       **✘**    ✔
`Revert Resized <#os-compute-specific>`_        **✘**    ✔
`Create Image <#os-compute-specific>`_          **✘**    ✔
.. `Reassign to project <#server-reassign>`_    .. ✔     .. **✘**
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

*Example (SOFT) Reboot Server: JSON*

.. code-block:: javascript

  {"reboot" : { "type": "SOFT"}}

Resize Server
.............

This operation changes the flavor of the server, which is the equivalent of
upgrading the hardware of a physical machine.

Request body contents::

  resize: {flavorRef: <flavor ID>}

*Example Resize Server: JSON*

.. code-block:: javascript

  {"resize" : { "flavorRef": 153}}

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

  firewallProfile: {profile: <firewall profile>, nic: <nic id>}

* **firewall profile** can be ``ENABLED``, ``DISABLED`` or ``PROTECTED``

*Example Action firewallProfile: JSON**

.. code-block:: javascript

  {"firewallProfile": {"profile": "ENABLED", "nic": 123}}

.. note:: Response body should be empty

Reassign Server
...............

This operation assigns the VM to a different project.
Each resource is assigned to a project. A Synnefo project is a set of resource
limits e.g., maximum number of CPU cores per user, maximum ammount of RAM, etc.

Although its resource is assigned exactly one project, a user may be a member
of more, so that different resources are registered to different projects.

Request body contents::

  reassign: { project: <project-id>}

*Example Action reassign: JSON**

.. code-block:: javascript

  {"reassign": {"project": "9969f2fd-86d8-45d6-9106-5e251f7dd92f"}}

.. note:: Response body should be empty

OS/Compute Specific
...................

The following operations are meaningless or not supported in the context of
Synnefo/Cyclades, but are parts of the OS/Compute API:

* `Change Administrator Password <http://docs.openstack.org/api/openstack-compute/2/content/Change_Password-d1e3234.html>`_
* `Rebuild Server <http://docs.openstack.org/api/openstack-compute/2/content/Rebuild_Server-d1e3538.html>`_
* `Confirm Resized Server <http://docs.openstack.org/api/openstack-compute/2/content/Confirm_Resized_Server-d1e3868.html>`_
* `Revert Resized Server <http://docs.openstack.org/api/openstack-compute/2/content/Revert_Resized_Server-d1e4024.html>`_
* `Create Image <http://docs.openstack.org/api/openstack-compute/2/content/Create_Image-d1e4655.html>`_

List Flavors
------------

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

  GET https://example.org/compute/v2.0/flavors

  {
    "flavors": [
      {
        "id": 1,
        "name": "One code",
        "links": [
            {
                "href": "https://example.org/compute/v2.0/flavors/1", 
                "rel": "self"
            }, 
            {
                "href": "https://example.org/compute/v2.0/flavors/1", 
                "rel": "bookmark"
            }
        ]
      }, {
        "id": 3,
        "name": "Four core",
        "links": [
            {
                "href": "https://example.org/compute/v2.0/flavors/3", 
                "rel": "self"
            }, 
            {
                "href": "https://example.org/compute/v2.0/flavors/3", 
                "rel": "bookmark"
            }
        ]
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

  GET https://example.org/compute/v2.0/flavors/detail

  {
    "flavors": [
      {
        "id": 1,
        "name": "One core",
        "ram": 1024,
        "SNF:disk_template": "drbd",
        "disk": 20,
        "vcpus": 1,
        "links": [
            {
                "href": "https://example.org/compute/v2.0/flavors/1", 
                "rel": "self"
            }, 
            {
                "href": "https://example.org/compute/v2.0/flavors/1", 
                "rel": "bookmark"
            }
        ]
      }, {
        "id": 3,
        "name": "Four core",
        "ram": 1024,
        "SNF:disk_template": "drbd",
        "disk": 40,
        "vcpus": 4,
        "links": [
            {
                "href": "https://example.org/compute/v2.0/flavors/3", 
                "rel": "self"
            }, 
            {
                "href": "https://example.org/compute/v2.0/flavors/3", 
                "rel": "bookmark"
            }
        ]
      }
    ]
  }

Get Flavor Details
------------------

.. rubric:: Request

======================= ====== ======== ==========
URI                     Method Cyclades OS/Compute
======================= ====== ======== ==========
``/flavors/<flavor-id`` GET    ✔        ✔
======================= ====== ======== ==========

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

All flavor attributes are `listed here <#flavor-ref>`_.

*Example Flavor Details: JSON*

  GET https://example.org/compute/v2.0/flavors/1

.. code-block:: javascript

  {
    "flavor": {
      {
        "id": 1,
        "name": "One core",
        "ram": 1024,
        "SNF:disk_template": "drbd",
        "disk": 20,
        "vcpus": 1,
        "links": [
            {
                "href": "https://example.org/compute/v2.0/flavors/1", 
                "rel": "self"
            }, 
            {
                "href": "https://example.org/compute/v2.0/flavors/1", 
                "rel": "bookmark"
            }
        ]
      }
    }
  }

List Images
-----------

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
        <image meta key>: <value>,
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

  GET https://example.org/compute/v2.0/images

  {
    "images: [
      {
        "status": "ACTIVE",
        "updated": "2013-03-02T15:57:03+00:00",
        "name": "Verbal description",
        "created": "2013-03-02T12:21:00+00:00",
        "id": "s0m3-1m4g3-1d",
        "links": [
          {
            "href": "https://example.org/compute/v2.0/images/s0m3-1m4g3-1d", 
            "rel": "self"
          }, 
          {
            "href": "https://example.org/compute/v2.0/images/s0m3-1m4g3-1d", 
            "rel": "bookmark"
          }
        ],
        "metadata": {
          "PARTITION_TABLE": "msdos",
          "OSFAMILY": "linux",
          "USERS": "root",
          "OS": "ubuntu",
        }
      }, {
        "status": "ACTIVE",
        "updated": "2013-03-02T15:57:03+00:00",
        "name": "edx_saas",
        "created": "2013-03-02T12:21:00+00:00",
        "progress": 100,
        "id": "07h3r-1m4g3-1d",
        "links": [
          {
            "href": "https://example.org/compute/v2.0/images/07h3r-1m4g3-1d", 
            "rel": "self"
          }, 
          {
            "href": "https://example.org/compute/v2.0/images/07h3r-1m4g3-1d", 
            "rel": "bookmark"
          }
        ],
        "metadata": {
          "PARTITION_TABLE": "ext3",
          "OSFAMILY": "Linux",
          "USERS": "root",
          "OS": "Debian"
        }
      }
    ]
  }

Get Image Details
-----------------

Get the details of a specific image

.. rubric:: Request

====================== ====== ======== ==========
URI                    Method Cyclades OS/Compute
====================== ====== ======== ==========
``/images/<image-id>`` GET    ✔        ✔
====================== ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

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
      <image meta key>: <value>
    }
  }

Image attributes are `listed here <#image-ref>`_.

*Example Details for an image with id 6404619d-...-aef57eaff4af, in JSON*

.. code-block:: javascript

  GET https://example.org/compute/v2.0/images/s0m3-1m4g3-1d

  {
    "image":
      {
        "status": "ACTIVE",
        "updated": "2013-03-02T15:57:03+00:00",
        "name": "Verbal description",
        "created": "2013-03-02T12:21:00+00:00",
        "id": "s0m3-1m4g3-1d",
        "links": [
          {
            "href": "https://example.org/compute/v2.0/images/s0m3-1m4g3-1d", 
            "rel": "self"
          }, 
          {
            "href": "https://example.org/compute/v2.0/images/s0m3-1m4g3-1d", 
            "rel": "bookmark"
          }
        ],
        "metadata": {
          "PARTITION_TABLE": "msdos",
          "OSFAMILY": "linux",
          "USERS": "root",
          "OS": "ubuntu",
        }
    }
}

Delete Image
------------

Delete an image, by changing its status from ``ACTIVE`` to ``DELETED``.

.. rubric:: Request

====================== ====== ======== ==========
URI                    Method Cyclades OS/Compute
====================== ====== ======== ==========
``/images/<image id>`` DELETE ✔        ✔
====================== ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

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
-------------------

.. rubric:: Request

=============================== ====== ======== ==========
URI                             Method Cyclades OS/Compute
=============================== ====== ======== ==========
``/images/<image-id>/metadata`` GET    ✔        ✔
=============================== ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

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
    <meta key>: <value>,
  ...
  }

*Example List Image Metadata: JSON*

.. code-block:: javascript

  GET https://example.org/compute/v2.0/images/s0m3-1m4g3-1d/metadata

  {
    "metadata": {
      "PARTITION_TABLE": "msdos",
      "OSFAMILY": "linux",
      "USERS": "root",
      "OS": "ubuntu",
    }
  }

.. note:: In OS/Compute API  the ``values`` level is missing from the response.

Update Image Metadata
---------------------

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

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

Request body content::

  metadata: {
    <meta key>: <value>,
    ...
  }

*Example Update Image Metadata Request: JSON*

.. code-block:: javascript

  POST https://example.org/compute/v2.0/images/s0m3-1m4g3-1d/metadata

  {"metadata": {"NewAttr": "NewVal", "OS": "Xubuntu'}}

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or image id
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this image
404 (Not Found)             Image or meta key not found
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
      "PARTITION_TABLE": "msdos",
      "OSFAMILY": "linux",
      "USERS": "root",
      "OS": "Xubuntu",
      "NEWATTR": "NewVal"
    }
  }

Get Image Metadata
------------------

.. rubric:: Request

===================================== ====== ======== ==========
URI                                   Method Cyclades OS/Compute
===================================== ====== ======== ==========
``/images/<image-id>/metadata/<key>`` GET    ✔        ✔
===================================== ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or image id
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to access this information
404 (Not Found)             Meta key not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Response body content::

  metadata: {<key>: <value>}

*Example Get Image Metadata Item: JSON*

.. code-block:: javascript

  GET https://example.org/compute/v2.0/images/s0m3-1m4g3-1d/metadata/OS

  {"metadata": {"OS": "Xubuntu"}}

.. note:: In OS/Compute, ``metadata`` is ``meta``

Update Image Metadata
---------------------

.. rubric:: Request

===================================== ====== ======== ==========
URI                                   Method Cyclades OS/Compute
===================================== ====== ======== ==========
``/images/<image-id>/metadata/<key>`` PUT    ✔        ✔
===================================== ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
Content-Type    Type or request body      required required
Content-Length  Length of request body    required required
==============  ========================= ======== ==========

.. note:: Request parameters should be empty

Request body content::

  metadata: {<key>: <value>}

*Example Update Image Metadata Item Request: JSON*

.. code-block:: javascript

  PUT https://example.org/compute/v2.0/images/s0m3-1m4g3-1d/metadata/OS
  {
    "metadata": {"OS": "Kubuntu"}
  }

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Request succeeded
400 (Bad Request)           Malformed request or image id
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this image
404 (Not Found)             Metadata key not found
413 (OverLimit)             Maximum number of metadata exceeded
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

Request body content::

  metadata: {<key>: <value>}

*Example Update Image Metadata Item Response: JSON*

.. code-block:: javascript

  {"metadata": {"OS": "Kubuntu"}}

Delete Image Metadata
---------------------

Delete an image metadata by its key.

.. rubric:: Request

===================================== ====== ======== ==========
URI                                   Method Cyclades OS/Compute
===================================== ====== ======== ==========
``/images/<image-id>/metadata/<key>`` DELETE ✔        ✔
===================================== ====== ======== ==========

|
==============  ========================= ======== ==========
Request Header  Value                     Cyclades OS/Compute
==============  ========================= ======== ==========
X-Auth-Token    User authentication token required required
==============  ========================= ======== ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Request succeeded
400 (Bad Request)           Malformed image ID
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this image
404 (Not Found)             Metadata key not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The server is not currently available
=========================== =====================

.. note:: In case of a 204 code, the response body should be empty.

Index of Attributes
-------------------

.. _server-ref:

Server Attributes
.................

=================== ======== ==========
Server attribute    Cyclades OS/Compute
=================== ======== ==========
id                  ✔        ✔
name                ✔        ✔
addresses           ✔        ✔
links               ✔        ✔
image               ✔        ✔
flavor              ✔        ✔
user_id             ✔        ✔
tenant_id           ✔        ✔
accessIPv4          ✔        ✔
accessIPv6          ✔        ✔
progress            ✔        ✔
status              ✔        ✔
updated             ✔        ✔
hostId              ✔        ✔
created             ✔        ✔
adminPass           ✔        ✔
metadata            ✔        ✔
suspended           ✔        **✘**
security_groups     ✔        **✘**
attachments         ✔        **✘**
config_drive        ✔        **✘**
SNF:fqdn            ✔        **✘**
key_name            ✔        **✘**
SNF:port_forwarding ✔        **✘**
SNF:task_state      ✔        **✘**
diagnostics         ✔        **✘**
deleted             ✔        **✘**
=================== ======== ==========

* **addresses** Networks related to this server. All information in this field
  is redundant, since it can be infered from the ``attachments`` field, but
  it is used for compatibility with OS/Computet

* **user_id** The UUID of the owner of the virtual server

* **tenant_id** The UUID of the project that defines this resource

* *hostId*, **accessIPv4** and **accessIPv6** are always empty and are used for
  compatibility with OS/Compute

* **progress** Shows the building progress of a virtual server. After the server
  is built, it is always ``100``

* **status** values are described `here <#status-ref>`_

* **updated** and **created** are date-formated

* **adminPass** is shown only once (in ``create server`` response). This
  information is not preserved in a clear text form, so it is not recoverable

* **suspended** is True only if the server is suspended by the cloud
  administrations or policy

* **progress** is a number between 0 and 100 and reflects the server building
  status

* **metadata** are custom key:value pairs. In Cyclades, the ``OS`` and
  ``USERS`` metadata are automatically retrieved from the servers image during
  creation

* **attachments** List of connection ports. Details `here <#attachments-ref>`_.

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

.. _attachments-ref:

Attachments (ports)
...................

In Cyclades, a port connects a virtual server to a public or private network.

Ports can be handled separately through the Cyclades/Network API.

In a virtual server context, a port may contain the following information:

================= ======================
Port Attributes    Description          
================= ======================
id                Port id            
mac_address       NIC's mac address     
network_id        Network ID
OS-EXT-IPS:type   ``fixed`` or ``floating``
firewallProfile   ``ENABLED``, ``DISABLED``, ``PROTECTED``
ipv4              IP v4 address
ipv6              IP v6 address
================= ======================

* **ipv4** and **ipv6** are mutually exclusive in practice, since a port
    either handles an IPv4, an IPv6, or none, but not both.

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
links rel         Atom link rel field  ✔        ✔
links href        Atom link href field ✔        ✔
================= ==================== ======== ==========

* **id** is the flavor unique id (a possitive integer)
* **name** is the flavor name (a string)
* **ram** is the server RAM size in MB
* **SNF:disk_template** is a reference to the underlying storage mechanism
  used by the Cyclades server (e.g., drdb, ext_elmc).
* **disk** the servers disk size in GB
* **vcpus** refer to the number of virtual CPUs assigned to a server
* **link ref** and **link href** refer to the Atom link attributes that are
  `used in OS/Compute API <http://docs.openstack.org/api/openstack-compute/2/content/List_Flavors-d1e4188.html>`_.

.. _image-ref:

Image
.....

An image is a collection of files you use to create or rebuild a server.

An image item may have the fields presented bellow:

================ ====================== ======== ==========
Image Attributes Description            Cyclades OS/Compute
================ ====================== ======== ==========
id               Image ID               ✔        ✔
name             Image name             ✔        ✔
updated          Last update date       ✔        ✔
created          Image creation date    ✔        ✔
progress         Ready status progress  ✔        **✘**
status           Image status           **✘**    ✔:
tenant_id        Image creator          **✘**    ✔
user_id          Image users            **✘**    ✔
metadata         Custom metadata        ✔        ✔
links            Atom links             **✘**    ✔
minDisk          Minimum required disk  **✘**    ✔
minRam           Minimum required RAM   **✘**    ✔
================ ====================== ======== ==========

* **id** is the image id and **name** is the image name. They are both strings.

* **updated** and **created** are both ISO8601 date strings

* **progress** varies between 0 and 100 and denotes the status of the image

* **metadata** is a collection of ``key``:``values`` pairs of custom metadata,
  under the tag ``values`` which lies under the tag ``metadata``.

* **tenant_id** The UUID of the project that defines this resource

.. note:: in OS/Compute, the ``values`` layer is missing
