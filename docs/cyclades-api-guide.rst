.. _cyclades-api-guide:

API Guide
*********

.. todo:: Document the relation of the API to the OpenStack API v1.1.

This is the guide to the REST API of the synnefo Compute Service.
It is meant for users wishing to make calls to the REST API directly.

The `kamaki <http://www.synnefo.org/docs/kamaki/latest/index.html>`_
command-line client and associated python library can be used instead of making
direct calls to :ref:`cyclades <cyclades>`.

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

* We only support the changes-since parameter in **List Servers** and **List
  Images**.
* We assume that garbage collection of deleted servers will only affect servers
  deleted ``POLL_TIME`` seconds in the past or earlier. Else we lose the
  information of a server getting deleted.
* Images do not support a deleted state, so we can not track deletions.


Versions
--------

* Version MIME type support is missing.
* Versionless requests are not supported.
* We hardcode the ``updated`` field in versions list
* Deployment note: The Atom metadata need to be fixed


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

* **List Servers** returns just ``id`` and ``name`` if details are not
  requested.
* **List Servers** can return 304 (even though not explicitly stated) when
  ``changes-since`` is given.

**Example List Servers: JSON**

.. code-block:: javascript

  {
      'servers':
          {'values': [
              {
                  'addresses': {'values': [
                          {
                              'id': 'public',
                              'mac': 'aa:00:00:49:2e:7e',
                              'name': 'public',
                              'values': [ {'addr': '192.168.32.6', 'version': 4} ]
                          }
                  ]},
                  'created': '2011-04-19T10:18:52.085737+00:00',
                  'flavorRef': 1,
                  'hostId': '',
                  'id': 1,
                  'imageRef': 3,
                  'metadata': {'values': {'foo': 'bar'}},
                  'name': 'My Server',
                  'status': 'ACTIVE',
                  'updated': u'2011-05-29T14:07:07.037602+00:00'
              },
              {
                  'addresses': {'values': [
                          {
                              'id': 'public',
                              'mac': 'aa:00:00:91:2f:df',
                              'name': 'public',
                              'values': [ {'addr': '192.168.32.7', 'version': 4} ]
                          },
                          {
                              'id': '2',
                              'mac': 'aa:00:00:c3:69:6f',
                              'name': 'private'
                          },
                  ]},
                  'created': '2011-05-02T20:51:08.527759+00:00',
                  'flavorRef': 1,
                  'hostId': '',
                  'id': 2,
                  'imageRef': 3,
                  'name': 'Other Server',
                  'progress': 0,
                  'status': 'ACTIVE',
                  'updated': '2011-05-29T14:59:11.267087+00:00'
              }
          ]
      }
  }


Get Server Stats
................

**GET** /servers/*id*/stats

**Normal Response Code**: 200

**Error Response Codes**: computeFault (400, 500), serviceUnavailable (503),
unauthorized (401), badRequest (400), itemNotFound (404), overLimit (413)

This operation returns URLs to graphs showing CPU and Network statistics. A
``refresh`` attribute is returned as well that is the recommended refresh rate
of the stats for the clients.

This operation does not require a request body.

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
  <stats xmlns="http://docs.openstack.org/compute/api/v1.1" xmlns:atom="http://www.w3.org/2005/Atom"
      serverRef="1"
      refresh="60"
      cpuBar="http://stats.okeanos.grnet.gr/b9a1c3ca7e3b9fce75112c43565fb9960b16048c/cpu-bar.png"
      cpuTimeSeries="http://stats.okeanos.grnet.gr/b9a1c3ca7e3b9fce75112c43565fb9960b16048c/cpu-ts.png"
      netBar="http://stats.okeanos.grnet.gr/b9a1c3ca7e3b9fce75112c43565fb9960b16048c/net-bar.png"
      netTimeSeries="http://stats.okeanos.grnet.gr/b9a1c3ca7e3b9fce75112c43565fb9960b16048c/net-ts.png">
  </stats>


Server Addresses
----------------

Server Actions
--------------

* **Change Password** is not supported.
* **Rebuild Server** is not supported.
* **Resize Server** is not supported.
* **Confirm Resized Server** is not supported.
* **Revert Resized Server** is not supported.

We have have extended the API with the following commands:


Start Server
............

**Normal Response Code**: 202

**Error Response Codes**: serviceUnavailable (503), itemNotFound (404)

The start function transitions a server from an ACTIVE to a STOPPED state.

**Example Action Start: JSON**:

.. code-block:: javascript

  {
      "start": {}
  }

This operation does not return a response body.


Shutdown Server
...............

**Normal Response Code**: 202

**Error Response Codes**: serviceUnavailable (503), itemNotFound (404)

The start function transitions a server from a STOPPED to an ACTIVE state.

**Example Action Shutdown: JSON**:

.. code-block:: javascript

  {
      "shutdown": {}
  }

This operation does not return a response body.


Get Server Console

**Normal Response Code**: 200

**Error Response Codes**: computeFault (400, 500), serviceUnavailable (503), unauthorized (401), badRequest (400), badMediaType(415), itemNotFound (404), buildInProgress (409), overLimit (413)

The console function arranges for an OOB console of the specified type. Only consoles of type "vnc" are supported for now.
    
It uses a running instance of vncauthproxy to setup proper VNC forwarding with a random password, then returns the necessary VNC connection info to the caller.

**Example Action Console: JSON**:

.. code-block:: javascript

  {
      "console": {
          "type": "vnc"
      }
  }

**Example Action Console Response: JSON**:

.. code-block:: javascript

  {
      "console": {
          "type": "vnc",
          "host": "vm42.ocean.grnet.gr",
          "port": 1234,
          "password": "IN9RNmaV"
      }
  }

**Example Action Console Response: XML**:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <console xmlns="http://docs.openstack.org/compute/api/v1.1" xmlns:atom="http://www.w3.org/2005/Atom"
      type="vnc"
      host="vm42.ocean.grnet.gr"
      port="1234"
      password="IN9RNmaV">
  </console>


Set Firewall Profile
....................

**Normal Response Code**: 202

**Error Response Codes**: computeFault (400, 500), serviceUnavailable (503),
unauthorized (401), badRequest (400), badMediaType(415), itemNotFound (404),
buildInProgress (409), overLimit (413)

The firewallProfile function sets a firewall profile for the public interface
of a server.

The allowed profiles are: **ENABLED**, **DISABLED** and **PROTECTED**.

**Example Action firewallProfile: JSON**:

.. code-block:: javascript

  {
      "firewallProfile": {
          "profile": "ENABLED"
      }
  }

This operation does not return a response body.


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


Metadata
--------

* **Update Server Metadata** and **Update Image Metadata** will only return the
  metadata that were updated (some could have been skipped).


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
