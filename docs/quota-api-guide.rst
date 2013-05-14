Resources
---------

Synnefo services offer *resources* to their users. Each type of resource is
registered in Astakos with a unique name. By convention, these names start
with the service name, e.g. ``cyclades.vm`` is a resource representing the
virtual machines offered by Cyclades.


Get Resource List
.................

**GET** /astakos/api/resources

This call returns a description for each resource available in the system.
The response consists of a dictionary, indexed by the resource name, which
contains a number of attributes for each resource.

**Response Codes**:

======  =====================
Status  Description
======  =====================
200     Success
500     Internal Server Error
======  =====================

**Example Successful Response**:

.. code-block:: javascript

  {
      "cyclades.vm": {
          "unit": null,
          "description": "Number of virtual machines",
          "service": "cyclades",
          "allow_in_projects": true
          },
      "cyclades.ram": {
          "unit": "bytes",
          "description": "Virtual machine memory",
          "service": "cyclades",
          "allow_in_projects": true
          }
  }

Quotas
------

The system specifies user quotas for each available resource. Resources
can be allocated from various sources. By default, users get resources
from a single source, called ``system``. For each combination of user,
source, and resource, the quota system keeps track of the maximum allowed
value (limit) and the current actual usage. The former is controlled by
the policy defined in Astakos; the latter is updated by the services that
actually implement the resource each time an allocation or deallocation
takes place.

Get Quotas
..........

**GET** /astakos/api/quotas

====================  =========================
Request Header Name   Value
====================  =========================
X-Auth-Token          User authentication token
====================  =========================

A user can query their resources with this call. It returns in a nested
dictionary structure, for each source and resource, three indicators.
``limit`` and ``usage`` are as explained above. ``pending`` is related to the
commissioning system explained below. Roughly, if ``pending`` is non zero,
this indicates that some resource allocation process has started but not
finished properly.

**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
401     Unauthorized (Missing token)
500     Internal Server Error
======  ============================

**Example Successful Response**:

.. code-block:: javascript

  {
      "system": {
          "cyclades.ram": {
              "usage": 536870912,
              "limit": 1073741824,
              "pending": 0

          },
          "cyclades.vm": {
              "usage": 2,
              "limit": 2,
              "pending": 0
          }
      },
      "project:1": {
          "cyclades.ram": {
              "usage": 2147483648,
              "limit": 2147483648,
              "pending": 0
          },
          "cyclades.vm": {
              "usage": 2,
              "limit": 5,
              "pending": 1
          }
      }
  }

Get Quotas per Service
......................

**GET** /astakos/api/service_quotas

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service authentication token
====================  ============================

A service can query the quotas for all resources related to it. By default,
it returns the quotas for all users, in the format explained above, indexed
by the user identifier (UUID).

Use the GET parameter ``?user=<uuid>`` to query for a single user.


**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
401     Unauthorized (Missing token)
500     Internal Server Error
======  ============================

**Example Successful Response**:

.. code-block:: javascript

  {
      "1a6165d0-5020-4b6d-a4ad-83476632a584": {
          "system": {
              "cyclades.ram": {
                  "usage": 536870912,
                  "limit": 1073741824,
                  "pending": 0
              },
              "cyclades.vm": {
                  "usage": 2,
                  "limit": 2,
                  "pending": 0
              }
          },
          "project:1": {
              "cyclades.ram": {
                  "usage": 2147483648,
                  "limit": 2147483648,
                  "pending": 0
              },
              "cyclades.vm": {
                  "usage": 2,
                  "limit": 5,
                  "pending": 1
              }
          }
      }
  }

Commissions
-----------

When a resource allocation is about to take place, the service that performs
this operation can query the quota system to find out whether the planned
allocation would surpass some defined limits. If this is not the case, the
quota system registers this pending allocation. Upon the actual allocation
of resources, the service informs the quota system to definitely update the
usage.

Thus, changing quotas consists of two steps: in the first, the service
issues a *commission*, indicating which extra resources will be given to
particular users; in the second, it finalizes the commission by *accepting*
it (or *rejecting*, if the allocation did not actually take place).

Issue Commission
................

**POST** /astakos/api/commissions

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service authentication token
====================  ============================

A service issues a commission by providing a list of *provisions*, i.e.
the intended allocation for a particular user (in general, ``holder``),
``source``, and ``resource`` combination.

The request body consists of a JSON dict (as in the example below), which
apart from the provisions list can also contain the following optional
fields:

 * ``name``: An optional description of the operation
 * ``force``: Succeed even if a limit is surpassed
 * ``auto_accept``: Perform the two steps at once

**Example Request**:

.. code-block:: javascript

  {
      "force": false,
      "auto_accept": false,
      "name": "an optional description",
      "provisions": [
          {
              "holder": "c02f315b-7d84-45bc-a383-552a3f97d2ad",
              "source": "system",
              "resource": "cyclades.vm",
              "quantity": 1
          },
          {
              "holder": "c02f315b-7d84-45bc-a383-552a3f97d2ad",
              "source": "system",
              "resource": "cyclades.ram",
              "quantity": 536870912
          }
      ]
  }

**Response Codes**:

======  =======================================================
Status  Description
======  =======================================================
201     Success
400     Commission failed due to invalid input data
401     Unauthorized (Missing token)
404     Cannot find one of the target holdings
413     A quantity fell below zero in one of the holdings
413     A quantity exceeded the capacity in one of the holdings
500     Internal Server Error
======  =======================================================

On a successful commission, the call responds with a ``serial``, an identifier
for the commission. On failure, in the case of ``overLimit`` (413) or
``itemNotFound`` (404), the returned cloudFault contains an extra field
``data`` with additional application-specific information. It contains at
least the ``provision`` that is to blame and the actual ``name`` of the
exception raised. In the case of ``overLimit``, ``limit`` and ``usage`` are
also included.

**Example Successful Response**:

.. code-block:: javascript

  {
      "serial": 57
  }

**Example Failure Response**:

.. code-block:: javascript

  {
      "overLimit": {
          "message": "a human-readable error message",
          "code": 413,
          "data": {
              "provision": {
                  "holder": "c02f315b-7d84-45bc-a383-552a3f97d2ad",
                  "source": "system",
                  "resource": "cyclades.vm",
                  "quantity": 1
              },
              "name": "NoCapacityError",
              "limit": 2,
              "usage": 2
          }
      }
  }

Get Pending Commissions
.......................

**GET** /astakos/api/commissions

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service authentication token
====================  ============================

The service can query the quota system for all *pending* commissions
initiated by itself, that is, all commissions that have been issued
but not accepted or rejected (see below). The call responds with the list
of the serials of all pending commissions.

**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
401     Unauthorized (Missing token)
500     Internal Server Error
======  ============================

**Example Successful Response**:

.. code-block:: javascript

  [<serial>, ...]

Get the Description of a Commission
...................................

**GET** /astakos/api/commissions/<serial>

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service authentication token
====================  ============================

This call allows a service to retrieve information for a pending commission.

**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
401     Unauthorized (Missing token)
404     Commission Not Found
500     Internal Server Error
======  ============================

**Example Successful Response**:

.. code-block:: javascript

  {
      "serial": 57,
      "issue_time": "2013-04-08T10:19:15.0373",
      "name": "an optional description",
      "provisions": [
          {
              "holder": "c02f315b-7d84-45bc-a383-552a3f97d2ad",
              "source": "system",
              "resource": "cyclades.vm",
              "quantity": 1
          },
          {
              "holder": "c02f315b-7d84-45bc-a383-552a3f97d2ad",
              "source": "system",
              "resource": "cyclades.ram",
              "quantity": 536870912
          }
      ]
  }

Accept or Reject a Commission
.............................

**POST** /astakos/api/commissions/<serial>/action

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service authentication token
====================  ============================

With this call a service can *accept* or *reject* a pending commission, that
is, finalize the registered usage or undo commission issued.
The system guarantees that a commission can always be later accepted
or rejected, no matter what other commissions have taken place in the meantime.

To accept, include in the request body a field indexed by ``accept``;
likewise for rejecting.

**Example Requests**:

.. code-block:: javascript

  {
      "accept": ""
  }

  {
      "reject": ""
  }

**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
401     Unauthorized (Missing token)
404     Commission Not Found
500     Internal Server Error
======  ============================

Accept or Reject Multiple Commissions
.....................................

**POST** /astakos/api/commissions/action

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service authentication token
====================  ============================

This allows to accept and reject multiple commissions in the same time,
by including the list of serials to accept and the list of serials to reject
in the request body.

**Example Request**:

.. code-block:: javascript

  {
      "accept": [56, 57],
      "reject": [56, 58, 59]
  }

The response includes the list of serials that have been actually
``accepted`` or ``rejected`` and those that ``failed``. The latter
consists of a list of pairs. The first element of the pair is a serial
that failed, the second element is a cloudFault describing the failure.

**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
401     Unauthorized (Missing token)
500     Internal Server Error
======  ============================

**Example Successful Response**:

.. code-block:: javascript

  { "accepted": [57],
    "rejected": [59],
    "failed": [
        [56, {
                 "badRequest": {
                     "message": "cannot both accept and reject serial 56",
                     "code": 400
                     }
                 }
        ],
        [58, {
                 "itemNotFound": {
                     "message": "serial 58 does not exist",
                     "code": 404
                     }
                 }
        ]
    ]
  }
