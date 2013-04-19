Resources
---------

Get Resource List
.................

**GET** /astakos/api/resources

**Normal Response Code**: 200

**Error Response Codes**:

======  =====================
Status  Description
======  =====================
500     Internal Server Error
======  =====================

**Example Successful Response**:

.. code-block:: javascript

  {
      "cyclades.vm": {
          "unit": null,
          "description": "Number of virtual machines",
          "service": "cyclades"
          },
      "cyclades.ram": {
          "unit": "bytes",
          "description": "Virtual machine memory",
          "service": "cyclades"
          }
  }

Quotas
------

Get Quotas
..........

**GET** /astakos/api/quotas

====================  =========================
Request Header Name   Value
====================  =========================
X-Auth-Token          User authentication token
====================  =========================

**Normal Response Code**: 200

**Error Response Codes**:

======  ============================
Status  Description
======  ============================
401     Unauthorized (Missing token)
500     Internal Server Error
======  ============================

**Example Successful Response**:

.. code-block:: javascript

  {
      "system": {
          "cyclades.ram": {
              "available": 536870912,
              "limit": 1073741824,
              "used": 536870912
          },
          "cyclades.vm": {
              "available": 0,
              "limit": 2,
              "used": 2
          }
      },
      "project:1": {
          "cyclades.ram": {
              "available": 0,
              "limit": 2147483648,
              "used": 2147483648
          },
          "cyclades.vm": {
              "available": 3,
              "limit": 5,
              "used": 2
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

Optional GET parameter: ?user=<uuid>

**Normal Response Code**: 200

**Error Response Codes**:

======  ============================
Status  Description
======  ============================
401     Unauthorized (Missing token)
500     Internal Server Error
======  ============================

**Example Successful Response**:

.. code-block:: javascript

  {
      "1a6165d0-5020-4b6d-a4ad-83476632a584": {
          "system": {
              "cyclades.ram": {
                  "available": 536870912,
                  "limit": 1073741824,
                  "used": 536870912
              },
              "cyclades.vm": {
                  "available": 0,
                  "limit": 2,
                  "used": 2
              }
          },
          "project:1": {
              "cyclades.ram": {
                  "available": 0,
                  "limit": 2147483648,
                  "used": 2147483648
              },
              "cyclades.vm": {
                  "available": 3,
                  "limit": 5,
                  "used": 2
              }
          }
      }
  }

Commissions
-----------

Issue Commission
................

**POST** /astakos/api/commissions

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service authentication token
====================  ============================

**Normal Response Code**: 201

**Error Response Codes**:

======  =======================================================
Status  Description
======  =======================================================
400     Commission failed due to invalid input data
401     Unauthorized (Missing token)
404     Cannot find one of the target holdings
413     A quantity fell below zero in one of the holdings
413     A quantity exceeded the capacity in one of the holdings
500     Internal Server Error
======  =======================================================

**Example Request**:

.. code-block:: javascript

  {
      "force": false,
      "auto_accept": false,
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

**Normal Response Code**: 200

**Error Response Codes**:

======  ============================
Status  Description
======  ============================
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

**Normal Response Code**: 200

**Error Response Codes**:

======  ============================
Status  Description
======  ============================
401     Unauthorized (Missing token)
404     Commission Not Found
500     Internal Server Error
======  ============================

**Example Successful Response**:

.. code-block:: javascript

  {
      "serial": 57,
      "issue_time": "2013-04-08T10:19:15.0373",
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

**Normal Response Code**: 200

**Error Response Codes**:

======  ============================
Status  Description
======  ============================
401     Unauthorized (Missing token)
404     Commission Not Found
500     Internal Server Error
======  ============================

**Example Requests**:

.. code-block:: javascript

  {
      "accept": ""
  }

  {
      "reject": ""
  }

Accept or Reject Multiple Commissions
.....................................

**POST** /astakos/api/commissions/action

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service authentication token
====================  ============================

**Normal Response Code**: 200

**Error Response Codes**:

======  ============================
Status  Description
======  ============================
401     Unauthorized (Missing token)
500     Internal Server Error
======  ============================

**Example Request**:

.. code-block:: javascript

  {
      "accept": [56, 57],
      "reject": [56, 58, 59]
  }

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
