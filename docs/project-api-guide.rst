Projects
--------

Astakos allows users to create *projects*. Through a project, one can ask for
additional resources on the virtual infrastructure for a certain amount of
time. All users admitted to the project gain access to these resources.


Retrieve List of Projects
.........................

**GET** /account/v1.0/projects

Returns all accessible projects. See below.

====================  =========================
Request Header Name   Value
====================  =========================
X-Auth-Token          User authentication token
====================  =========================

The request can include the following filters as GET parameters:
``state``, ``owner``, ``name``.

It also supports parameter ``mode`` with possible values: ``member``,
``default``. The former restricts the result to active projects where the
request user is an active member. By default it returns all accessible
projects; see below.

**Example Request**:

.. code-block:: javascript

GET /account/v1.0/projects?state=active&owner=uuid

**Response Codes**:

======  =====================
Status  Description
======  =====================
200     Success
400     Bad Request
401     Unauthorized (Missing token)
500     Internal Server Error
======  =====================

**Example Successful Response**:

List of project details. See below.

Retrieve a Project
..................

**GET** /account/v1.0/projects/<proj_id>

====================  =========================
Request Header Name   Value
====================  =========================
X-Auth-Token          User authentication token
====================  =========================

A project is accessible when the request user is admin, project owner,
applicant or member, or the project is active.

**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
401     Unauthorized (Missing token)
403     Forbidden
404     Not Found
500     Internal Server Error
======  ============================

**Example Successful Response**:

.. code-block:: javascript

  {
      "id": proj_id,
      "state": "uninitialized" | "active" | "suspended" | "terminated" | "deleted",
      "creation_date": "2013-06-26T11:48:06.579100+00:00",
      "name": "name",
      "owner": uuid,
      "homepage": homepage,
      "description": description,
      "end_date": date,
      "join_policy": "auto" | "moderated" | "closed",
      "leave_policy": "auto" | "moderated" | "closed",
      "max_members": int,
      "private": boolean,
      "system_project": boolean,
      "resources": {"cyclades.vm": {"project_capacity": int,
                                    "member_capacity": int
                                   }
                   }
      "last_application": last application or null,
      "deactivation_date": date  # if applicable
  }

Create a Project
................

**POST** /account/v1.0/projects

====================  =========================
Request Header Name   Value
====================  =========================
X-Auth-Token          User authentication token
====================  =========================

**Example Request**:

.. code-block:: javascript

  {
      "name": name,
      "owner": uuid,  # if omitted, request user assumed
      "homepage": homepage,  # optional
      "description": description,  # optional
      "comments": comments,  # optional
      "start_date": date,  # optional
      "end_date": date,
      "join_policy": "auto" | "moderated" | "closed",  # default: "moderated"
      "leave_policy": "auto" | "moderated" | "closed",  # default: "auto"
      "max_members": int, # optional
      "private": boolean, # default: false
      "resources": {"cyclades.vm": {"project_capacity": int,
                                    "member_capacity": int
                                   }
                   }
  }

**Response Codes**:

======  ============================
Status  Description
======  ============================
201     Created
400     Bad Request
401     Unauthorized (Missing token)
403     Forbidden
409     Conflict
500     Internal Server Error
======  ============================

**Example Successful Response**:

.. code-block:: javascript

  {
      "id": project_id,
      "application": application_id
  }


Modify a Project
................

**PUT** /account/v1.0/projects/<proj_id>

====================  =========================
Request Header Name   Value
====================  =========================
X-Auth-Token          User authentication token
====================  =========================


**Example Request**:

As above.

**Response Codes**:

======  ============================
Status  Description
======  ============================
201     Created
400     Bad Request
401     Unauthorized (Missing token)
403     Forbidden
404     Not Found
409     Conflict
500     Internal Server Error
======  ============================

**Example Successful Response**:

As above.

Take Action on a Project
........................

**POST** /account/v1.0/projects/<proj_id>/action

====================  =========================
Request Header Name   Value
====================  =========================
X-Auth-Token          User authentication token
====================  =========================

**Example Request**:

.. code-block:: javascript

  {
      <action>: {"reason": reason,
                 "app_id": app_id  # only for app related actions
                }
  }

<action> can be: "suspend", "unsuspend", "terminate", "reinstate",
"approve", "deny", "dismiss", "cancel". The last four actions operate on the
project's last application and require its ``app_id``.

**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
400     Bad Request
401     Unauthorized (Missing token)
403     Forbidden
404     Not Found
409     Conflict
500     Internal Server Error
======  ============================

Retrieve List of Memberships
............................

**GET** /account/v1.0/projects/memberships

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          User authentication token
====================  ============================

Get all accessible memberships. Filtering by project is possible via the GET
parameter ``project``.

**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
400     Bad Request
401     Unauthorized (Missing token)
500     Internal Server Error
======  ============================

**Example Successful Response**

List of memberships. See below.

Retrieve a Membership
.....................

**GET** /account/v1.0/projects/memberships/<memb_id>

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          User authentication token
====================  ============================

A membership is accessible if the request user is admin, project owner or
the member.

**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
401     Unauthorized (Missing token)
403     Forbidden
404     Not Found
500     Internal Server Error
======  ============================

**Example Successful Response**

.. code-block:: javascript

  {
      "id": id,
      "user": uuid,
      "project": project_id,
      "state": "requested" | "accepted" | "leave_requested" | "suspended" | "rejected" | "cancelled" | "removed",
      "requested": last_request_date,
      "accepted": last_acceptance_date,
      "removed": last_removal_date,
      "allowed_actions": ["leave", "cancel", "accept", "reject", "remove"],
  }

Take Action on a Membership
...........................

**POST** /account/v1.0/projects/memberships/<memb_id>/action

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          User authentication token
====================  ============================

**Example Request**

.. code-block:: javascript

  {
      <action>: "reason"
  }

<action> can be one of: "leave", "cancel", "accept", "reject", "remove"

**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
400     Bad Request
401     Unauthorized (Missing token)
403     Forbidden
404     Not Found
409     Conflict
500     Internal Server Error
======  ============================

Create a Membership
...................

**POST** /account/v1.0/projects/memberships

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          User authentication token
====================  ============================

**Example Requests**

.. code-block:: javascript

  {
      "join": {
          "project": proj_id
      }
  }

.. code-block:: javascript

  {
      "enroll": {
          "project": proj_id,
          "user": "user@example.org"
      }
  }

**Response Codes**:

======  ============================
Status  Description
======  ============================
200     Success
400     Bad Request
401     Unauthorized (Missing token)
403     Forbidden
409     Conflict
500     Internal Server Error
======  ============================

**Example Response**

.. code-block:: javascript

  {
      "id": membership_id
  }
