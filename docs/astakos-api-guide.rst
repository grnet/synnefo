Astakos API 
===========

This is Astakos API guide.

Overview
--------


Astakos service co-ordinates the access to resources (and the subsequent
permission model) and acts as the single point of registry and entry to the
GRNET cloud services.

This document's goals is to describe the APIs to the outer world.
Make sure you have read the :ref:`astakos` general architecture first.

Document Revisions
^^^^^^^^^^^^^^^^^^

=========================  ================================
Revision                   Description
=========================  ================================
0.6 (June 06, 2012)        Split service and admin API.
0.1 (Feb 10, 2012)         Initial release.
=========================  ================================

Admin API Operations
--------------------

The operations described in this chapter allow users to authenticate themselves and priviledged users (ex. helpdesk) to access other user information.

Most of the operations require a valid token assigned to users having the necessary permissions.

.. _authenticate-api-label:

Authenticate
^^^^^^^^^^^^

Authenticate API requests require a token. An application that wishes to connect to Astakos, but does not have a token, should redirect the user to ``/login``. (see :ref:`authentication-label`)

==================== =========  ==================
Uri                  Method     Description
==================== =========  ==================
``/im/authenticate`` GET        Authenticate user using token
==================== =========  ==================

|

====================  ===========================
Request Header Name   Value
====================  ===========================
X-Auth-Token          Authentication token
====================  ===========================

Extended information on the user serialized in the json format will be returned:

===========================  ============================
Name                         Description
===========================  ============================
username                     User uniq identifier
uniq                         User email (uniq identifier used by Astakos)
auth_token                   Authentication token
auth_token_expires           Token expiration date
auth_token_created           Token creation date
has_credits                  Whether user has credits
has_signed_terms             Whether user has aggred on terms
groups                       User groups
===========================  ============================

Example reply:

::

  {"username": "4ad9f34d6e7a4992b34502d40f40cb",
  "uniq": "user@example.com"
  "auth_token": "0000",
  "auth_token_expires": "Fri, 29 Jun 2012 10:03:37 GMT",
  "auth_token_created": "Wed, 30 May 2012 10:03:37 GMT",
  "has_credits": false,
  "has_signed_terms": true}

|

=========================== =====================
Return Code                 Description
=========================== =====================
204 (No Content)            The request succeeded
400 (Bad Request)           Method not allowed or no user found
401 (Unauthorized)          Missing token or inactive user or penging approval terms
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

Get User by email
^^^^^^^^^^^^^^^^^

Returns a json formatted dictionary containing information about a specific user

============================== =========  ==================
Uri                            Method     Description
============================== =========  ==================
``/im/admin/api/v2.0/users/``  GET        Get user information by email
============================== =========  ==================

|

====================  ===========================
Request Header Name   Value
====================  ===========================
X-Auth-Token          Authentication token owned by
                      a user having or inheriting ``im.can_access_userinfo`` permission
====================  ===========================

|

======================  =========================
Request Parameter Name  Value
======================  =========================
name                    Email
======================  =========================


|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           Method not allowed
401 (Unauthorized)          Missing or invalid token or unauthorized user
404 (Not Found)             Missing email or inactive user
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

Example reply:

::

    {"username": "7e530044f90a4e7ba2cb94f3a26c40",
    "auth_token_created": "Wed, 30 May 2012 10:03:37 GMT",
    "name": "Firstname Surname",
    "groups": ["default"],
    "user_permissions": [],
    "has_credits": false,
    "auth_token_expires":"Fri, 29 Jun 2012 10:03:37 GMT",
    "enabled": true,
    "email": ["user@example.com"],
    "id": 4}

Get User by username
^^^^^^^^^^^^^^^^^^^^

Returns a json formatted dictionary containing information about a specific user

======================================== =========  ==================
Uri                                      Method     Description
======================================== =========  ==================
``/im/admin/api/v2.0/users/{username}``  GET        Get user information by username
======================================== =========  ==================

|

====================  ===========================
Request Header Name   Value
====================  ===========================
X-Auth-Token          Authentication token owned
                      by a user having or inheriting ``im.can_access_userinfo`` permission
====================  ===========================

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           Method not allowed
401 (Unauthorized)          Missing or invalid token or unauthorized user
404 (Not Found)             Invalid username
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

Example reply:

::

    {"username": "7e530044f90a4e7ba2cb94f3a26c40",
    "auth_token_created": "Wed, 30 May 2012 10:03:37 GMT",
    "name": "Firstname Surname",
    "groups": ["default"],
    "user_permissions": [],
    "has_credits": false,
    "auth_token_expires":
    "Fri, 29 Jun 2012 10:03:37 GMT",
    "enabled": true,
    "email": ["user@example.com"],
    "id": 4}

Get Services
^^^^^^^^^^^^

Returns a json formatted list containing information about the supported cloud services.

==================== =========  ==================
Uri                  Method     Description
==================== =========  ==================
``/im/get_services`` GET        Get cloud services
==================== =========  ==================

Example reply:

::

    [{"url": "/", "icon": "home-icon.png", "name": "grnet cloud", "id": "1"},
    {"url": "/okeanos.html", "name": "~okeanos", "id": "2"},
    {"url": "/ui/", "name": "pithos+", "id": "3"}]


Get Menu
^^^^^^^^

Returns a json formatted list containing the cloud bar links. 

==================== =========  ==================
Uri                  Method     Description
==================== =========  ==================
``/im/get_menu``     GET        Get cloud bar menu
==================== =========  ==================

Example reply if request user is not authenticated:

::

    [{"url": "/im/", "name": "Sign in"}]

Example reply if request user is authenticated:

::

    [{"url": "/im/login", "name": "user@example.com"},
    {"url": "/im/profile", "name": "My account"},
    {"url": "/im/logout", "name": "Sign out"}]

Service API Operations
----------------------

The operations described in this chapter allow services to access user information and perform specific tasks.

The operations require a valid service token.

Send feedback
^^^^^^^^^^^^^

Via this operaton services can post user feedback requests.

========================= =========  ==================
Uri                       Method     Description
========================= =========  ==================
``/im/service/feedback``  POST       Send feedback
========================= =========  ==================

|

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service Authentication token
====================  ============================

|

======================  =========================
Request Parameter Name  Value
======================  =========================
auth_token              User token
feedback_msg            Feedback message
feedback_data           Additional information about service client status
======================  =========================

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           Method not allowed or missing or invalid user token parameter or invalid message data
401 (Unauthorized)          Missing or expired service token
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

Get User by email
^^^^^^^^^^^^^^^^^

Returns a json formatted dictionary containing information about a specific user

================================ =========  ==================
Uri                              Method     Description
================================ =========  ==================
``/im/service/api/v2.0/users/``  GET        Get user information by email
================================ =========  ==================

|

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service Authentication token
====================  ============================

|

======================  =========================
Request Parameter Name  Value
======================  =========================
name                    Email
======================  =========================

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           Method not allowed
401 (Unauthorized)          Missing or expired or invalid service token
404 (Not Found)             Missing email or inactive user
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

Example reply:

::

    {"username": "7e530044f90a4e7ba2cb94f3a26c40",
    "auth_token_created": "Wed, 30 May 2012 10:03:37 GMT",
    "name": "Firstname Surname",
    "groups": ["default"],
    "user_permissions": [],
    "has_credits": false,
    "auth_token_expires":"Fri, 29 Jun 2012 10:03:37 GMT",
    "enabled": true,
    "email": ["user@example.com"],
    "id": 4}

Get User by username
^^^^^^^^^^^^^^^^^^^^

Returns a json formatted dictionary containing information about a specific user

========================================== =========  ==================
Uri                                        Method     Description
========================================== =========  ==================
``/im/service/api/v2.0/users/{username}``  GET        Get user information by username
========================================== =========  ==================

|

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service Authentication token
====================  ============================

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           Method not allowed
401 (Unauthorized)          Missing or expired or invalid service token
404 (Not Found)             Invalid username
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

Example reply:

::

    {"username": "7e530044f90a4e7ba2cb94f3a26c40",
    "auth_token_created": "Wed, 30 May 2012 10:03:37 GMT",
    "name": "Firstname Surname",
    "groups": ["default"],
    "user_permissions": [],
    "has_credits": false,
    "auth_token_expires":
    "Fri, 29 Jun 2012 10:03:37 GMT",
    "enabled": true,
    "email": ["user@example.com"],
    "id": 4}
