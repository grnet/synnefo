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
0.14 (May 14, 2013)        Do not serve user quotas in :ref:`authenticate-api-label`
0.14 (May 02, 2013)        Change URIs (keep also the old ones until the next version)
0.13 (January 21, 2013)    Extend api to export user presentation & quota information.
0.6 (June 06, 2012)        Split service and user API.
0.1 (Feb 10, 2012)         Initial release.
=========================  ================================

Get Services
^^^^^^^^^^^^

Returns a json formatted list containing information about the supported cloud services.

============================= =========  ==================
Uri                           Method     Description
============================= =========  ==================
``/im/get_services``          GET        Get cloud services
============================= =========  ==================

Example reply:

::

    [{"url": "/", "icon": "home-icon.png", "name": "grnet cloud", "id": "1"},
    {"url": "/okeanos.html", "name": "~okeanos", "id": "2"},
    {"url": "/ui/", "name": "pithos+", "id": "3"}]


Get Menu
^^^^^^^^

Returns a json formatted list containing the cloud bar links.

========================= =========  ==================
Uri                       Method     Description
========================= =========  ==================
``/im/get_menu``          GET        Get cloud bar menu
========================= =========  ==================

Example reply if request user is not authenticated:

::

    [{"url": "/im/", "name": "Sign in"}]

Example reply if request user is authenticated:

::

    [{"url": "/im/", "name": "user@example.com"},
    {"url": "/im/landing", "name": "Dashboard"},
    {"url": "/im/logout", "name": "Sign out"}]


User API Operations
--------------------

The operations described in this chapter allow users to authenticate themselves, send feedback and get user uuid/displayname mappings.

All the operations require a valid user token.

.. _authenticate-api-label:

Authenticate
^^^^^^^^^^^^

Authenticate API requests require a token. An application that wishes to connect to Astakos, but does not have a token, should redirect the user to ``/login``. (see :ref:`authentication-label`)

============================= =========  ==================
Uri                           Method     Description
============================= =========  ==================
``/astakos/api/authenticate`` GET        Authenticate user using token
============================= =========  ==================

|

====================  ===========================
Request Header Name   Value
====================  ===========================
X-Auth-Token          User authentication token
====================  ===========================

Extended information on the user serialized in the json format will be returned:

===========================  ============================
Name                         Description
===========================  ============================
displayname                     User displayname
uuid                         User unique identifier
email                        List with user emails
name                         User full name
auth_token_created           Token creation date
auth_token_expires           Token expiration date
usage                        List of user resource usage (if usage request parameter is present)
===========================  ============================

Example reply:

::

  {"id": "12",
  "displayname": "user@example.com",
  "uuid": "a9dc21d2-bcb2-4104-9a9e-402b7c70d6d8",
  "email": "[user@example.com]",
  "name": "Firstname Lastname",
  "auth_token_created": "Wed, 30 May 2012 10:03:37 GMT",
  "auth_token_expires": "Fri, 29 Jun 2012 10:03:37 GMT"}

|

=========================== =====================
Return Code                 Description
=========================== =====================
204 (No Content)            The request succeeded
400 (Bad Request)           Method not allowed or no user found
401 (Unauthorized)          Missing token or inactive user or penging approval terms
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

.. warning:: The service is also available under ``/im/authenticate``.
     It  will be removed in the next version.


Send feedback
^^^^^^^^^^^^^

Post user feedback.

========================= =========  ==================
Uri                       Method     Description
========================= =========  ==================
``/astakos/api/feedback``  POST       Send feedback
========================= =========  ==================

|

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          User authentication token
====================  ============================

|

======================  =========================
Request Parameter Name  Value
======================  =========================
feedback_msg            Feedback message
feedback_data           Additional information about service client status
======================  =========================

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
502 (Bad Gateway)           Send feedback failure
400 (Bad Request)           Method not allowed or invalid message data
401 (Unauthorized)          Missing or expired user token
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

.. warning:: The service is also available under ``/feedback``.
     It  will be removed in the next version.

Get User catalogs
^^^^^^^^^^^^^^^^^

Return a json formatted dictionary containing information about a specific user

================================ =========  ==================
Uri                              Method     Description
================================ =========  ==================
``/astakos/api/user_catalogs``    POST       Get 2 catalogs containing uuid to displayname mapping and the opposite
================================ =========  ==================

|

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          User authentication token
====================  ============================

|

The request body is a json formatted dictionary containing a list with uuids and another list of displaynames to translate.

Example request content:

::

  {"displaynames": ["user1@example.com", "user2@example.com"],
   "uuids":["ff53baa9-c025-4d56-a6e3-963db0438830", "a9dc21d2-bcb2-4104-9a9e-402b7c70d6d8"]}

Example reply:

::

  {"displayname_catalog": {"user1@example.com": "a9dc21d2-bcb2-4104-9a9e-402b7c70d6d8",
                           "user2@example.com": "816351c7-7405-4f26-a968-6380cf47ba1f"},
  'uuid_catalog': {"a9dc21d2-bcb2-4104-9a9e-402b7c70d6d8": "user1@example.com",
                   "ff53baa9-c025-4d56-a6e3-963db0438830": "user2@example.com"}}


|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           Method not allowed or request body is not json formatted
401 (Unauthorized)          Missing or expired or invalid user token
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

.. warning:: The service is also available under ``/user_catalogs``.
     It  will be removed in the next version.

Service API Operations
----------------------

The operations described in this chapter allow services to get user uuid/displayname mappings.

All the operations require a valid service token.

Get User catalogs
^^^^^^^^^^^^^^^^^

Return a json formatted dictionary containing information about a specific user

===================================== =========  ==================
Uri                                   Method     Description
===================================== =========  ==================
``/astakos/api/service/user_catalogs`` POST       Get 2 catalogs containing uuid to displayname mapping and the opposite
===================================== =========  ==================

|

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          Service authentication token
====================  ============================

|

The request body is a json formatted dictionary containing a list with uuids and another list of displaynames to translate.
If instead of list null is passed then the response contains the information for all the system users (For discretion purposes
this behavior is **not** exposed in the respective call of the User API).

Example request content:

::

  {"displaynames": ["user1@example.com", "user2@example.com"],
   "uuids":["ff53baa9-c025-4d56-a6e3-963db0438830", "a9dc21d2-bcb2-4104-9a9e-402b7c70d6d8"]}

Example reply:

::

  {"displayname_catalog": {"user1@example.com": "a9dc21d2-bcb2-4104-9a9e-402b7c70d6d8",
                           "user2@example.com": "816351c7-7405-4f26-a968-6380cf47ba1f"},
  'uuid_catalog': {"a9dc21d2-bcb2-4104-9a9e-402b7c70d6d8": "user1@example.com",
                   "ff53baa9-c025-4d56-a6e3-963db0438830": "user2@example.com"}}


|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           Method not allowed or request body is not json formatted
401 (Unauthorized)          Missing or expired or invalid service token
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

.. warning:: The service is also available under ``/service/api/user_catalogs``.
     It  will be removed in the next version.
