Astakos API 
===========

This is Astakos API guide.

Overview
--------

Astakos serves as the point of authentication for GRNET (http://www.grnet.gr)
services. It is a platform-wide service, allowing users to register, login, and
keep track of permissions.

Users in astakos can be authenticated via several identity providers:

 * Local
 * Twitter
 * Shibboleth

It provides also a command line tool for managing user accounts.

It is build over django and extends its authentication mechanism.

This document's goals is to describe the APIs to the outer world.
Make sure you have read the :ref:`astakos` general architecture first.

The present document is meant to be read alongside the Django documentation
(https://www.djangoproject.com/). Thus, it is suggested that the reader is
familiar with associated technologies.

Document Revisions
^^^^^^^^^^^^^^^^^^

=========================  ================================
Revision                   Description
=========================  ================================
0.1 (Feb 10, 2012)         Initial release.
=========================  ================================

API Operations
--------------

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
===========================  ============================

Example reply:

::

  {"username": "4ad9f34d6e7a4992b34502d40f40cb",
  "uniq": "papagian@example.com"
  "auth_token": "0000",
  "auth_token_expires": "Tue, 11-Sep-2012 09:17:14 ",
  "auth_token_created": "Sun, 11-Sep-2011 09:17:14 ",
  "has_credits": false,
  "has_signed_terms": true}

|

=========================== =====================
Return Code                 Description
=========================== =====================
204 (No Content)            The request succeeded
400 (Bad Request)           The request is invalid
401 (Unauthorized)          Missing token or inactive user or penging approval terms
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

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

[{"url": "/", "icon": "home-icon.png", "name": "grnet cloud", "id": "cloud"},
 {"url": "/okeanos.html", "name": "~okeanos", "id": "okeanos"},
 {"url": "/ui/", "name": "pithos+", "id": "pithos"}]
 
Get Menu
^^^^^^^^

Returns a json formatted list containing the cloud bar links. 

==================== =========  ==================
Uri                  Method     Description
==================== =========  ==================
``/im/get_menu``     GET        Get cloud bar menu
==================== =========  ==================

|

======================  =========================
Request Parameter Name  Value
======================  =========================
location                Location to pass in the next parameter
======================  =========================

Example reply if request user is not authenticated:

::

[{"url": "/im/login?next=", "name": "login..."}]

Example reply if request user is authenticated::

    [{"url": "/im/profile", "name": "user@grnet.gr"},
     {"url": "/im/profile", "name": "view your profile..."},
     {"url": "/im/password", "name": "change your password..."},
     {"url": "/im/feedback", "name": "feedback..."},
     {"url": "/im/logout", "name": "logout..."}]




