.. _network-api-guide:

Cyclades/Network API Guide
^^^^^^^^^^^^^^^^^^^^^^^^^^

Introduction
============

The Network Service of `Synnefo <http://www.synnefo.org>`_ is implemented as
part of Cyclades. It exposes the OpenStack `Networking ("Neutron") API
<http://api.openstack.org/api-ref-networking.html>`_ and some
`extensions <file:///home/saxtouri/src/synnefo/docs/_build/html/network-api-guide.html>`_
with minor modifications if needed.

This document's goals are:

* Define the Cyclades/Network REST API
* Clarify the differences between Cyclades/Network and OpenStack Neutron

API Operations
==============

.. rubric:: Networks

====================================== ================================= ====== ======== ======= ==========
Description                            URI                               Method Cyclades/Network OS/Neutron
====================================== ================================= ====== ================ ==========
`List <#list-networks>`__              ``/networks``                     GET    ✔                ✔
`Get details <#get-network-details>`__ ``/networks/<network-id>``        GET    ✔                ✔
`Create <#create-network>`__           ``/networks``                     POST   ✔                ✔
Bulk creation                          ``/networks``                     POST   **✘**            ✔
`Update <#update-network>`__           ``/networks/<network-id>``        PUT    ✔                ✔
`Delete <#delete-network>`__           ``/networks/<network id>``        DELETE ✔                ✔
`Reassign <#reassign-network>`__       ``/networks/<network-id>/action`` POST   ✔                **✘**
====================================== ================================= ====== ================ ==========

.. rubric:: Subnets

===================================== ======================== ====== ======== ======= ==========
Description                           URI                      Method Cyclades/Network OS/Neutron
===================================== ======================== ====== ================ ==========
`List <#list-subnets>`__              ``/subnets``             GET    ✔                ✔
`Get details <#get-subnet-details>`__ ``/subnets/<subnet-id>`` GET    ✔                ✔
`Create <#create-subnet>`__           ``/subnets``             POST   ✔                ✔
Bulk creation                         ``/subnets``             POST   **✘**            ✔
`Update <#update-subnet>`__           ``/subnets/<subnet-id>`` PUT    ✔                ✔
Delete                                ``/subnets/<subnet-id>`` DELETE **✘**            ✔
===================================== ======================== ====== ================ ==========

.. rubric:: Ports

=================================== ==================== ====== ======== ======= ==========
Description                         URI                  Method Cyclades/Network OS/Neutron
=================================== ==================== ====== ================ ==========
`List <#list-ports>`__              ``/ports``           GET    ✔                ✔
`Get details <#get-port-details>`__ ``/ports/<port-id>`` GET    ✔                ✔
`Create <#create-port>`__           ``/ports``           POST   ✔                ✔
Bulk creation                       ``/ports``           POST   **✘**            ✔
`Update <#update-port>`__           ``/ports/<port-id>`` PUT    ✔                ✔
`Delete <#delete-port>`__           ``/ports/<port id>`` DELETE ✔                ✔
=================================== ==================== ====== ================ ==========

.. rubric:: Floating IPs

========================================== ======================================= ====== ================ ==========
Description                                URI                                     Method Cyclades/Network OS/Neutron Extensions
========================================== ======================================= ====== ================ ==========
`List <#list-floating-ips>`__              ``/floatingips``                        GET    ✔                ✔
`Get details <#get-floating-ip-details>`__ ``/floatingips/<floatingip-id>``        GET    ✔                ✔
`Create <#create-floating-ip>`__           ``/floatingips``                        POST   ✔                ✔
Update                                     ``/floatingips/<floatingip-id>``        PUT    **✘**            ✔
`Delete <#delete-floating-ip>`__           ``/floatingips/<floatingip id>``        DELETE ✔                ✔
`Reassign <#reassign-floating-ip>`__       ``/floatingips/<floatingip-id>/action`` POST   ✔                **✘**
========================================== ======================================= ====== ================ ==========

List networks
-------------

List networks accessible by the user

.. rubric:: Request

============= ====== ================ ==========
URI           Method Cyclades/Network OS/Neutron
============= ====== ================ ==========
``/networks`` GET    ✔                ✔
============= ====== ================ ==========

|

==============  ========================= ================ ==========
Request Header  Value                     Cyclades/Network OS/Neutron
==============  ========================= ================ ==========
X-Auth-Token    User authentication token required         required
==============  ========================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
401 (Unauthorized)          Missing or expired user token
=========================== =====================


Response body contents::

  networks: [
    {
      <network attribute>: <value>,
      ...
    }, ...
  ]

The attributes of a network are listed `here <#network-ref>`__.

*Example List Networks: JSON*

.. code-block:: javascript

  GET https://example.org/network/v2.0/networks


  {
    "networks": [
      {
        "id": 2718
        "name": "Public IPv6 Network"
        "status": "ACTIVE"
        "router:externa"l: true
        "updated": "2013-12-18T11:11:12.272389+00:00"
        "user_id": None
        "links":[
          {
            "href": "https://example.org/network/v2.0/networks/2718"
            "rel": "self"
          }, {
            "href": "https://example.org/network/v2.0/networks/2718"
            "rel": "bookmark"
          }
        ]
        "created": "2013-12-17T17:15:48.617049+00:00"
        "tenant_id": None
        "admin_state_up": true
        "SNF:floating_ip_pool": false
        "public": true
        "subnets":[
          28
        ]
        "type": "IP_LESS_ROUTED",
        "public": true
      }, {
        "id": "3141",
        "name": "My Private Network",
        "status": "ACTIVE",
        "router:external": false,
        "updated": "2014-02-13T09:40:05.195945+00:00",
        "user_id": "s0m3-u5e7-1d",
        "links": [
          {
              "href": "https://example.org/network/v2.0/networks/3141",
              "rel": "self"
          },
          {
              "href": "https://example.org/network/v2.0/networks/3141",
              "rel": "bookmark"
          }
        ],
        "created": "2014-02-13T09:40:05.101008+00:00",
        "tenant_id": "s0m3-u5e7-1d",
        "admin_state_up": true,
        "type": "MAC_FILTERED",
        "subnets": [],
        "SNF:floating_ip_pool": false,
        "public": false
      }
    ]
  }


Get network details
-------------------

.. rubric:: Request

========================== ====== ================ ==========
URI                        Method Cyclades/Network OS/Neutron
========================== ====== ================ ==========
``/networks/<network id>`` GET    ✔                ✔
========================== ====== ================ ==========

|

==============  ========================= ================ ==========
Request Header  Value                     Cyclades/Network OS/Neutron
==============  ========================= ================ ==========
X-Auth-Token    User authentication token required         required
==============  ========================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
401 (Unauthorized)          Missing or expired user token
404 (itemNoFound)           Network not found
=========================== =====================

Response body contents::

  network: {
    <network attribute>: <value>,
    ...
  }

The attributes of a network are listed `here <#network-ref>`__.

*Example Get Network Details: JSON*

.. code-block:: javascript

  GET https://example.org/network/v2.0/networks/3141


  {
    "network": {
      "id": "3141",
      "name": "My Private Network",
      "status": "ACTIVE",
      "router:external": false,
      "updated": "2014-02-13T09:40:05.195945+00:00",
      "user_id": "s0m3-u5e7-1d",
      "links": [
        {
            "href": "https://example.org/network/v2.0/networks/3141",
            "rel": "self"
        },
        {
            "href": "https://example.org/network/v2.0/networks/3141",
            "rel": "bookmark"
        }
      ],
      "created": "2014-02-13T09:40:05.101008+00:00",
      "tenant_id": "s0m3-u5e7-1d",
      "admin_state_up": true,
      "type": "MAC_FILTERED",
      "subnets": [],
      "SNF:floating_ip_pool": false,
      "public": false
    }
  }

Create network
--------------

.. rubric:: Request

============= ====== ================ ==========
URI           Method Cyclades/Network OS/Neutron
============= ====== ================ ==========
``/networks`` POST   ✔                ✔
============= ====== ================ ==========

|

==============  ========================= ================ ==========
Request Header  Value                     Cyclades/Network OS/Neutron
==============  ========================= ================ ==========
X-Auth-Token    User authentication token required         required
Content-Type    Type or request body      required         required
Content-Length  Length of request body    required         required
==============  ========================= ================ ==========

Request body contents::

  network: {
    <network attribute>: <value>,
    ...
  }

================= ================ ==========
Network Attribute Cyclades/Network OS/Neutron
================= ================ ==========
type              required         **✘**
name              ✔                ✔
admin_state_up    **✘**            ✔
shared            **✘**            ✔
tenand_id         **✘**            ✔
================= ================ ==========

* **type** Valid values are the same as in ``network_type`` of
  `a network <#network-ref>`_.

* **name** a string

* **admin_state_up**, **shared** and **tenantd_id** are accepted by
  Cyclades/Network, but they are ignored

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Network created
400 (BadRequest)            Invalid request body (invalid or missing type)
401 (Unauthorized)          Missing or expired user token
404 (itemNoFound)           Network not found
=========================== =====================

In case of success, the response has the same format is in
`get network details <#get-network-details>`_.

Update network
--------------

.. rubric:: Request

========================== ====== ================ ==========
URI                        Method Cyclades/Network OS/Neutron
========================== ====== ================ ==========
``/networks/<network id>`` PUT    ✔                ✔
========================== ====== ================ ==========

|

==============  ========================= ================ ==========
Request Header  Value                     Cyclades/Network OS/Neutron
==============  ========================= ================ ==========
X-Auth-Token    User authentication token required         required
Content-Type    Type or request body      required         required
Content-Length  Length of request body    required         required
==============  ========================= ================ ==========

Request body contents::

  network: {
    <network attribute>: <value>,
    ...
  }

================= ================ ==========
Network Attribute Cyclades/Network OS/Neutron
================= ================ ==========
name              ✔                ✔
network_id        **✘**            ✔
admin_state_up    **✘**            ✔
shared            **✘**            ✔
tenand_id         **✘**            ✔
================= ================ ==========

* **name** a string

* **network_id**, **admin_state_up**, **shared** and **tenantd_id** are
  accepted by   Cyclades/Network, but they are ignored

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Network is updated
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             You are not the owner of the network
404 (itemNoFound)           Network not found
=========================== =====================

In case of success, the response has the same format is in
`get network details <#get-network-details>`_ containing the updated values.

Delete network
--------------

.. rubric:: Request

========================== ====== ================ ==========
URI                        Method Cyclades/Network OS/Neutron
========================== ====== ================ ==========
``/networks/<network id>`` DELETE ✔                ✔
========================== ====== ================ ==========

|

==============  ========================= ================ ==========
Request Header  Value                     Cyclades/Network OS/Neutron
==============  ========================= ================ ==========
X-Auth-Token    User authentication token required         required
==============  ========================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Network is deleted
401 (Unauthorized)          Missing or expired user token
404 (itemNoFound)           Network not found
409 (Conflict)              The network is being used
=========================== =====================

.. note:: *409 (Confict)* is raised when there are ports connected to the
  network or floating IPs reserved from its pool. The subnets that are
  connected to it, though, are automatically deleted upon network deletion.

Reassign Network
----------------

Assign a network to a different project.

.. rubric:: Request

================================= ====== ================ ==========
URI                               Method Cyclades/Network OS/Neutron
================================= ====== ================ ==========
``/networks/<network-id>/action`` POST   ✔                **✘**
================================= ====== ================ ==========

|

==============  =========================
Request Header  Value
==============  =========================
X-Auth-Token    User authentication token
==============  =========================

Request body contents::

  reassign: {
      project: <project-id>
   }

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this network (e.g. public)
404 (Not Found)             Network not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================

List subnets
------------

List subnets of networks accessible by the user

.. rubric:: Request

============ ====== ================ ==========
URI          Method Cyclades/Network OS/Neutron
============ ====== ================ ==========
``/subnets`` GET    ✔                ✔
============ ====== ================ ==========

|

============== ========================= ================ ==========
Request Header Value                     Cyclades/Network OS/Neutron
============== ========================= ================ ==========
X-Auth-Token   User authentication token required         required
============== ========================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
401 (Unauthorized)          Missing or expired user token
=========================== =====================

Response body contents::

  subnets: [
    {
      <subnet attribute>: <value>,
      ...
    }, ...
  ]

The attributes of a subnet are listed `here <#subnet-ref>`__.

*Example List subnets: JSON*

.. code-block:: javascript

  GET https://example.org/network/v2.0/subnets

  {
    "subnets": [
      {
        "user_id": null,
        "name": "IPv6 Subnet of Network 2718",
        "links": [
            {
                "href": "https://example.org/network/v2.0/subnets/8172",
                "rel": "self"
            },
            {
                "href": "https://example.org/network/v2.0/subnets/8172",
                "rel": "bookmark"
            }
        ],
        "network_id": "2718",
        "tenant_id": null,
        "dns_nameservers": [],
        "enable_slaac": true,
        "public": true,
        "allocation_pools": [],
        "host_routes": [],
        "ip_version": 6,
        "gateway_ip": "2001:123:4abc:5678::9",
        "cidr": "2001:876:5cba:4321::/64",
        "enable_dhcp": true,
        "id": "8172"
      }, {
        "user_id": "s0m3-u5e7-1d",
        "name": "IPv6 Subnet of Network 3141",
        "links": [
            {
                "href": "https://example.org/network/v2.0/subnets/1413",
                "rel": "self"
            },
            {
                "href": "https://example.org/network/v2.0/subnets/1413",
                "rel": "bookmark"
            }
        ],
        "network_id": "3141",
        "tenant_id": "s0m3-u5e7-1d",
        "dns_nameservers": [],
        "enable_slaac": false,
        "public": false,
        "allocation_pools": [],
        "host_routes": [],
        "ip_version": 6,
        "gateway_ip": "2001:321:4abc:8765::9",
        "cidr": "2001:678:5cba:1234::/64",
        "enable_dhcp": true,
        "id": "1413"
      }
    ]
  }


Get subnet details
------------------

.. rubric:: Request

======================== ====== ================ ==========
URI                      Method Cyclades/Network OS/Neutron
======================== ====== ================ ==========
``/subnets/<subnet id>`` GET    ✔                ✔
======================== ====== ================ ==========

|

============== ========================= ================ ==========
Request Header Value                     Cyclades/Network OS/Neutron
============== ========================= ================ ==========
X-Auth-Token   User authentication token required         required
============== ========================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Request succeeded
401 (Unauthorized)          Missing or expired user token
404 (itemNoFound)           Subnet not found
=========================== =====================

Response body contents::

  subnet: {
    <subnet attribute>: <value>,
    ...
  }

The attributes of a subnet are listed `here <#subnet-ref>`__.

*Example Get subnet Details: JSON*

.. code-block:: javascript

  GET https://example.org/network/v2.0/subnets/1413


  {
    "subnet": {
        "user_id": "s0m3-u5e7-1d",
        "name": "IPv6 Subnet of Network 3141",
        "links": [
            {
                "href": "https://example.org/network/v2.0/subnets/1413",
                "rel": "self"
            },
            {
                "href": "https://example.org/network/v2.0/subnets/1413",
                "rel": "bookmark"
            }
        ],
        "network_id": "3141",
        "tenant_id": "s0m3-u5e7-1d",
        "dns_nameservers": [],
        "enable_slaac": false,
        "public": false,
        "allocation_pools": [],
        "host_routes": [],
        "ip_version": 6,
        "gateway_ip": "2001:321:4abc:8765::9",
        "cidr": "2001:678:5cba:1234::/64",
        "enable_dhcp": true,
        "id": "1413"
      }
  }

Create subnet
--------------

.. rubric:: Request

============ ====== ================ ==========
URI          Method Cyclades/Network OS/Neutron
============ ====== ================ ==========
``/subnets`` POST   ✔                ✔
============ ====== ================ ==========

|

==============  ========================= ================ ==========
Request Header  Value                     Cyclades/Network OS/Neutron
==============  ========================= ================ ==========
X-Auth-Token    User authentication token required         required
Content-Type    Type or request body      required         required
Content-Length  Length of request body    required         required
==============  ========================= ================ ==========

Request body contents::

  subnet: {
    <subnet attribute>: <value>,
    ...
  }

================= ================ ==========
Subnet Attribute  Cyclades/Network OS/Neutron
================= ================ ==========
network_id        required         required
cidr              required         required
fixed_ips         ✔                ✔
name              ✔                ✔
tenand_id         **✘**            ✔
allocation_pools  ✔                ✔
gateway_ip        ✔                ✔
ip_version        ✔                ✔
id                **✘**            ✔
enable_dhcp       ✔                ✔
================= ================ ==========

* All the attributes are explained `here <#subnet-ref>`__.

* **ip_version** must be set to 6 if ``cidr`` is an IPc6 subnet

* **tenand_id** and **id** are accepted but ignored

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Network created
400 (BadRequest)            Invalid request body (missing network_id or cidr)
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Insufficient permissions
404 (itemNoFound)           Network not found
409 (Conflict)              Allocation pools overlap with themselves or gateway
=========================== =====================

In case of success, the response has the same format is in
`get subnet details <#get-subnet-details>`_.

Update subnet
-------------

.. rubric:: Request

======================== ====== ================ ==========
URI                      Method Cyclades/Network OS/Neutron
======================== ====== ================ ==========
``/subnets/<subnet id>`` PUT    ✔                ✔
======================== ====== ================ ==========

|

============== ========================= ================ ==========
Request Header Value                     Cyclades/Network OS/Neutron
============== ========================= ================ ==========
X-Auth-Token   User authentication token required         required
Content-Type   Type or request body      required         required
Content-Length Length of request body    required         required
============== ========================= ================ ==========

Request body contents::

  subnet: {
    <subnet attribute>: <value>,
    ...
  }

================= ================ ==========
Subnet Attribute  Cyclades/Network OS/Neutron
================= ================ ==========
network_id        **✘**            ✔
cidr              **✘**            ✔
fixed_ips         **✘**            ✔
name              ✔                ✔
tenand_id         **✘**            ✔
allocation_pools  **✘**            ✔
gateway_ip        **✘**            ✔
ip_version        **✘**            ✔
id                **✘**            ✔
enable_dhcp       **✘**            ✔
================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Network is updated
400 (BadRequest)            Field is not modifiable
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             You are not the owner of this subnet
404 (itemNoFound)           Subnet not found
=========================== =====================

In case of success, the response has the same format as in
`get subnet details <#get-subnet-details>`_ containing the updated values.

List ports
----------

List ports connected on servers and networks accessible by the user

.. rubric:: Request

========== ====== ================ ==========
URI        Method Cyclades/Network OS/Neutron
========== ====== ================ ==========
``/ports`` GET    ✔                ✔
========== ====== ================ ==========

|

============== ========================= ================ ==========
Request Header Value                     Cyclades/Network OS/Neutron
============== ========================= ================ ==========
X-Auth-Token   User authentication token required         required
============== ========================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
401 (Unauthorized)          Missing or expired user token
=========================== =====================


Response body contents::

  ports: [
    {
      <port attribute>: <value>,
      ...
    }, ...
  ]

The attributes of a port are listed `here <#port-ref>`__.

*Example List Ports: JSON*

.. code-block:: javascript

  GET https://example.org/network/v2.0/ports

  {
    "ports": [
      {
        "status": "ACTIVE",
        "updated": "2014-02-12T08:32:41.785217+00:00",
        "user_id": "s0m3-u5e7-1d",
        "name": "Port to public network",
        "links": [
            {
                "href": "https://example.org/network/v2.0/ports/18",
                "rel": "self"
            },
            {
                "href": "https://example.org/network/v2.0/ports/18",
                "rel": "bookmark"
            }
        ],
        "admin_state_up": true,
        "network_id": "2718",
        "tenant_id": "s0m3-u5e7-1d",
        "created": "2014-02-12T08:31:37.782907+00:00",
        "device_owner": "vm",
        "mac_address": "aa:01:02:6c:34:ab",
        "fixed_ips": [
            {
                "subnet": "28",
                "ip_address": "2001:443:2dfc:1232:a810:3cf:fe9b:21ab"
            }
        ],
        "id": "18",
        "security_groups": [],
        "device_id": "42"
      }, {
        "status": "ACTIVE",
        "updated": "2014-02-15T08:32:41.785217+00:00",
        "user_id": "s0m3-u5e7-1d",
        "name": "Port to public network",
        "links": [
            {
                "href": "https://example.org/network/v2.0/ports/19",
                "rel": "self"
            },
            {
                "href": "https://example.org/network/v2.0/ports/19",
                "rel": "bookmark"
            }
        ],
        "admin_state_up": true,
        "network_id": "2719",
        "tenant_id": "s0m3-u5e7-1d",
        "created": "2014-02-15T08:31:37.782907+00:00",
        "device_owner": "vm",
        "mac_address": "aa:00:0c:6d:34:bb",
        "fixed_ips": [
            {
                "subnet": "29",
                "ip_address": "192.168.1.2"
            }
        ],
        "id": "19",
        "security_groups": [],
        "device_id": "42"
      }
    ]
  }


Get port details
----------------

.. rubric:: Request

==================== ====== ================ ==========
URI                  Method Cyclades/Network OS/Neutron
==================== ====== ================ ==========
``/ports/<port id>`` GET    ✔                ✔
==================== ====== ================ ==========

|

============== ========================= ================ ==========
Request Header Value                     Cyclades/Network OS/Neutron
============== ========================= ================ ==========
X-Auth-Token   User authentication token required         required
============== ========================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
401 (Unauthorized)          Missing or expired user token
404 (itemNoFound)           Port not found
=========================== =====================

Response body contents::

  port: {
    <port attribute>: <value>,
    ...
  }

The attributes of a port are listed `here <#port-ref>`__.

*Example Get Port Details: JSON*

.. code-block:: javascript

  GET https://example.org/network/v2.0/ports/18


  {
    "port": {
      "status": "ACTIVE",
      "updated": "2014-02-12T08:32:41.785217+00:00",
      "user_id": "s0m3-u5e7-1d",
      "name": "Port to public network",
      "links": [
        {
            "href": "https://example.org/network/v2.0/ports/18",
            "rel": "self"
        },
        {
            "href": "https://example.org/network/v2.0/ports/18",
            "rel": "bookmark"
        }
      ],
      "admin_state_up": true,
      "network_id": "2718",
      "tenant_id": "s0m3-u5e7-1d",
      "created": "2014-02-12T08:31:37.782907+00:00",
      "device_owner": "vm",
      "mac_address": "aa:01:02:6c:34:ab",
      "fixed_ips": [
        {
            "subnet": "28",
            "ip_address": "2001:443:2dfc:1232:a810:3cf:fe9b:21ab"
        }
      ],
      "id": "18",
      "security_groups": [],
      "device_id": "42"
      }
  }

Create port
--------------

.. rubric:: Request

========== ====== ================ ==========
URI        Method Cyclades/Network OS/Neutron
========== ====== ================ ==========
``/ports`` POST   ✔              ✔
========== ====== ================ ==========

|

==============  ========================= ================ ==========
Request Header  Value                     Cyclades/Network OS/Neutron
==============  ========================= ================ ==========
X-Auth-Token    User authentication token required         required
Content-Type    Type or request body      required         required
Content-Length  Length of request body    required         required
==============  ========================= ================ ==========

Request body contents::

  port: {
    <port attribute>: <value>,
    ...
  }

=============== ================ ==========
Port Attribute  Cyclades/Network OS/Neutron
=============== ================ ==========
network_id      required         required
device_id       ✔                **✘**
fixed_ips       ✔                ✔
name            ✔                ✔
security_groups ✔                ✔
admin_state_up  **✘**            ✔
mac_address     **✘**            ✔
tenand_id       **✘**            ✔
=============== ================ ==========

* **network_id** is the uuid of the network this port is connected to

* **device_id** is the id of the device (i.e. server or router) this port is
  connected to

* **fixed_ips** is a list of IP items. Each IP item is a dictionary containing
  an ``ip_address`` field. The value must be the IPv4 address of a floating IP
  which is reserved from the pool of the network with ``network_id``, for the
  current user

* **name** a string

* **security_groups** is a list of security group IDs

* **admin_state_up**, **mac_address** and **tenantd_id** are accepted by
  Cyclades/Network, but they are ignored

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Network created
400 (BadRequest)            Invalid request body (missing network_id)
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Insufficient permissions
404 (itemNoFound)           Network not found
503 (macGenerationFailure)  Mac address generation failed
=========================== =====================

In case of success, the response has the same format is in
`get port details <#get-port-details>`_.

Update port
-----------

.. rubric:: Request

========================== ====== ================ ==========
URI                        Method Cyclades/Network OS/Neutron
========================== ====== ================ ==========
``/ports/<port id>`` PUT    ✔                ✔
========================== ====== ================ ==========

|

============== ========================= ================ ==========
Request Header Value                     Cyclades/Network OS/Neutron
============== ========================= ================ ==========
X-Auth-Token   User authentication token required         required
Content-Type   Type or request body      required         required
Content-Length Length of request body    required         required
============== ========================= ================ ==========

Request body contents::

  port: {
    <port attribute>: <value>,
    ...
  }

=============== ================ ==========
Port Attribute  Cyclades/Network OS/Neutron
=============== ================ ==========
name            ✔                ✔
network_id      **✘**            ✔
port_id         **✘**            ✔
fixed_ips       **✘**            ✔
security_groups **✘**            ✔
admin_state_up  **✘**            ✔
mac_address     **✘**            ✔
tenand_id       **✘**            ✔
=============== ================ ==========


* **name** a string

* all other attributes are accepted but ignored

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Network is updated
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             You are not the owner of the network
404 (itemNoFound)           Network not found
=========================== =====================

In case of success, the response has the same format as in
`get port details <#get-port-details>`_ containing the updated values.

Delete port
-----------

Delete a port

.. rubric:: Request

========================== ====== ================ ==========
URI                        Method Cyclades/Network OS/Neutron
========================== ====== ================ ==========
``/ports/<port id>``       DELETE ✔                ✔
========================== ====== ================ ==========

|

==============  ========================= ================ ==========
Request Header  Value                     Cyclades/Network OS/Neutron
==============  ========================= ================ ==========
X-Auth-Token    User authentication token required         required
==============  ========================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Port is being deleted
401 (Unauthorized)          Missing or expired user token
404 (itemNoFound)           Port not found
=========================== =====================

List floating ips
-----------------

List the floating ips which are reserved by the user

.. rubric:: Request

================ ====== ================ ==========
URI              Method Cyclades/Network OS/Neutron Extensions
================ ====== ================ ==========
``/floatingips`` GET    ✔                ✔
================ ====== ================ ==========

|

============== ========================= ================ ==========
Request Header Value                     Cyclades/Network OS/Neutron Extensions
============== ========================= ================ ==========
X-Auth-Token   User authentication token required         required
============== ========================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
401 (Unauthorized)          Missing or expired user token
=========================== =====================

Response body contents::

  floatingips: [
    {
      <floating ip attribute>: <value>,
      ...
    }, ...
  ]

The attributes of a floating ip are listed `here <#floating-ip-ref>`__.

*Example List Floating IPs: JSON*

.. code-block:: javascript

  GET https://example.org/network/v2.0/floatingips

  {
    "floatingips": [
      {
        "instance_id": 42
        "floating_network_id": 2719
        "fixed_ip_address": None
        "floating_ip_address": "192.168.1.2"
        "port_id": 19
      },
      {
        "instance_id": 84
        "floating_network_id": 4178
        "fixed_ip_address": None
        "floating_ip_address": 192.168.1.3
        "port_id": 38
      }
    ]
  }

Get floating ip details
-----------------------

.. rubric:: Request

======================== ====== ================ =====================
URI                      Method Cyclades/Network OS/Neutron Extensions
======================== ====== ================ =====================
``/floatingips/<ip-id>`` GET    ✔                ✔
======================== ====== ================ =====================

|

============== ========================= ================ ==========
Request Header Value                     Cyclades/Network OS/Neutron Extensions
============== ========================= ================ ==========
X-Auth-Token   User authentication token required         required
============== ========================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Request succeeded
401 (Unauthorized)          Missing or expired user token
404 (itemNoFound)           Floating IP not found
=========================== =====================

Response body contents::

  floatingip: {
    <floating ip attribute>: <value>,
    ...
  }

The attributes of a floating ip are listed `here <#floating-ip-ref>`__.

*Example Get Floating IP Details: JSON*

.. code-block:: javascript

  GET https://example.org/network/v2.0/floatingips/19


  {
    "floatingip": {
      "instance_id": 42
      "floating_network_id": 2719
      "fixed_ip_address": None
      "floating_ip_address": "192.168.1.2"
      "port_i"d: 19
    }
  }

Create floating ip
------------------

.. rubric:: Request

================ ====== ================ =====================
URI              Method Cyclades/Network OS/Neutron Extensions
================ ====== ================ =====================
``/floatingips`` POST   ✔              ✔
================ ====== ================ =====================

|

============== ========================= ================ =====================
Request Header Value                     Cyclades/Network OS/Neutron Extensions
============== ========================= ================ =====================
X-Auth-Token   User authentication token required         required
Content-Type   Type or request body      required         required
Content-Length Length of request body    required         required
============== ========================= ================ =====================

Request body contents::

  floating ip: {
    <floating ip attribute>: <value>,
    ...
  }

===================== ================ ==========
Floating IP Attribute Cyclades/Network OS/Neutron Extensions
===================== ================ ==========
floating_network_id   ✔                required
floating_ip_address   ✔                ✔
port_id               **✘**            ✔
fixed_ip_address      **✘**            ✔
===================== ================ ==========

* In Cyclades/Network, if ``floating_network_id`` is not used, the service
  will automatically pick a public network with a sufficient number of
  available IPs

* All the attributes are explained `here <#floating-ip-ref>`__.

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
201 (OK)                    Network created
400 (BadRequest)            Invalid request body (missing floating_network_id)
401 (Unauthorized)          Missing or expired user token
409 (Conflict)              Insufficient resources
=========================== =====================

In case of success, the response has the same format is in
`get floating ip details <#get-floating-ip-details>`_.

Delete floating ip
------------------

.. rubric:: Request

================================ ====== ================ =====================
URI                              Method Cyclades/Network OS/Neutron Extensions
================================ ====== ================ =====================
``/floatingips/<floatingip-id>`` DELETE ✔                ✔
================================ ====== ================ =====================

|

==============  ========================= ================ ==========
Request Header  Value                     Cyclades/Network OS/Neutron Extensions
==============  ========================= ================ ==========
X-Auth-Token    User authentication token required         required
==============  ========================= ================ ==========

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
204 (OK)                    Floating IP is being deleted
401 (Unauthorized)          Missing or expired user token
404 (itemNoFound)           Floating IP not found
=========================== =====================

Reassign floating ip
--------------------

Assign a floating IP to a different project.

.. rubric:: Request

======================================= ====== ================ ==========
URI                                     Method Cyclades/Network OS/Neutron
======================================= ====== ================ ==========
``/floatingips/<floatingip-id>/action`` POST   ✔                **✘**
======================================= ====== ================ ==========

|

==============  =========================
Request Header  Value
==============  =========================
X-Auth-Token    User authentication token
==============  =========================

Request body contents::

  reassign: {
      project: <project-id>
   }

.. rubric:: Response

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    Request succeeded
400 (Bad Request)           Malformed request
401 (Unauthorized)          Missing or expired user token
403 (Forbidden)             Not allowed to modify this network (e.g. public)
404 (Not Found)             Network not found
500 (Internal Server Error) The request cannot be completed because of an
\                           internal error
503 (Service Unavailable)   The service is not currently available
=========================== =====================


Index of Attributes
-------------------

.. _network-ref:

Network attributes
..................

================== ================ ==========
Network attributes Cyclades/Network OS/Neutron
================== ================ ==========
admin_state_up     ✔                ✔
id                 ✔                ✔
name               ✔                ✔
shared             ✔                ✔
public             ✔                **✘**
status             ✔                ✔
subnets            ✔                ✔
tenant_id          ✔                ✔
user_id            ✔                **✘**
network_type       ✔                **✘**
router:external    ✔                **✘**
SNF:floating_ip    ✔                **✘**
links              ✔                **✘**
================== ================ ==========

* **admin_state_up** The administrative state of the network (true, false)
* **shared** Used for compatibility with OS/Neutron and has the same value as
  public
* **public** If the network is publicly accessible (true, false)
* **status** ACTIVE, DOWN, BUILD, ERROR, SNF:DRAINED
  The later means that no new ports or floating IPs can be created from this
  network
* **tenant_id** Used for compatibility with OS/Neutron and has the same value
  as user_id
* **user_id** The owner of the network if private or None if public
* **network_type** MAC_FILTERED, IP_LESS_ROUTED, PHYSICAL_VLAN
* **router:external**  Whether the network is connected to an external router
  (true, false)

.. _subnet-ref:

Subnet attributes
.................

================= ================ ==========
Subnet attributes Cyclades/Network OS/Neutron
================= ================ ==========
id                ✔                ✔
name              ✔                ✔
network_id        ✔                ✔
ip_version        ✔                ✔
cidr              ✔                ✔
gateway_ip        ✔                ✔
enable_dhcp       ✔                ✔
allocation_pools  ✔                ✔
tenant_id         ✔                ✔
dns_nameservers   ✔                ✔
host_routes       ✔                ✔
user_id           ✔                **✘**
enable_slaac      ✔                **✘**
links             ✔                **✘**
================= ================ ==========

* **id** The UUID for the subnet
* **name** A human readable name
* **network_id** The ID of the network associated with this subnet
* **ip_version** The IP version (4, 6) of the subnet (default is 4)
* **cidr** CIDR represents IP range for this subnet, based on the IP version
* **gateway_ip** Default gateway used by devices in this subnet. If not
  specified the service will be the first available IP address. Tto get no
  gateway, set to None
* **enable_dhcp** Wheather nfdhcpd is enabled for this subnet (true, false)
* **enable_slaac** Whether SLAAC is enabled for this subnet (true, false)
* **allocation_pools(CR)** Subranges of cidr available for dynamic allocation.
  List of dictionaries of the form:
  [{“start”: “192.168.2.0”, “end”: 192.168.2.10”}, ...]
* **user_id** The UUID of the network owner, None if the network is public
* **tenant_id** The UUID of the project that defines this resource
* **host_routes** Routes that should be used by devices with IPs from this
  subnet (list)
* **dns_nameservers** Used for compatibility with OpenStack/Neutron

.. _port-ref:

Port attributes
...............

==================== ================ ==========
Port attributes      Cyclades/Network OS/Neutron
==================== ================ ==========
id                   ✔                ✔
name                 ✔                ✔
status               ✔                ✔
admin_state_up       ✔                ✔
network_id           ✔                ✔
tenant_id            ✔                ✔
mac_address          ✔                ✔
fixed_ips            ✔                ✔
device_id            ✔                ✔
device_owner         ✔                ✔
security_groups      ✔                ✔
port_filter          **✘**            ✔
binding:vif_type     **✘**            ✔
binding:capabilities **✘**            ✔
user_id              ✔                **✘**
links                ✔                **✘**
==================== ================ ==========

* **status** ACTIVE, DOWN, BUILD, ERROR
* **admin_state_up** The administrative state of the network (true, false). If
  false, the network does not forward packets
* **network_id**  UUID of the attached network
* **user_id** The UUID of the owner of the network, or None if the network is
  public
* **tenant_id** The UUID of the project that defines this resource
* **device_owner** ID of the entity using this port. e.g.,
  network:router, network:router_gateway
* **fixed_ips** IP information for the port (list of dicts). Each IP item
  (dictionary) consists of a ``subnet`` and an ``ip_address`` field.
* **device_id** The ID of the device that uses this port i.e., a virtual server
  or a router

* **security_groups** List of security group IDs associated with this port

.. _floating-ip-ref:

Floating ip attributes
......................

====================== ================ ==========
Floating ip attributes Cyclades/Network OS/Neutron Extensions
====================== ================ ==========
id                     ✔                ✔
floating_network_id    ✔                ✔
floating_ip_address    ✔                ✔
fixed_ip_address       ✔                ✔
port_id                ✔                ✔
user_id                ✔                **✘**
tenant_id              ✔                ✔
instance_id            ✔                **✘**
router_id              ✔                ✔
====================== ================ ==========


* **id** The UUID for the floating IP
* **floating_network_id** The UUID of the external network associated to this
  floating IP is associated.
* **floating_ip_address** The IPv4 address of the floating IP
* **fixed_ip_address** Used for compatibility, always None
* **port_id** The port where this IP is attached, if any
* **instance_id** The device using this floating IP, if any
* **user_id** The UUID of the owner of the floating IP
* **tenant_id** The UUID of the project that defines this resource
* **router_id** The ID of the router, if any
