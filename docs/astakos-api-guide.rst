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
0.14 (May 28, 2013)        Extend token api with authenticate call
0.14 (May 23, 2013)        Extend api to list endpoints
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
    {"url": "/ui/", "name": "pithos", "id": "3"}]


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

============================== =========  ==================
Uri                            Method     Description
============================== =========  ==================
``/account/v1.0/authenticate`` GET        Authenticate user using token
============================== =========  ==================

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

========================== =========  ==================
Uri                        Method     Description
========================== =========  ==================
``/account/v1.0/feedback`` POST       Send feedback
========================== =========  ==================

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

=============================== =========  ==================
Uri                             Method     Description
=============================== =========  ==================
``/account/v1.0/user_catalogs`` POST       Get 2 catalogs containing uuid to displayname mapping and the opposite
=============================== =========  ==================

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

======================================= =========  ==================
Uri                                     Method     Description
======================================= =========  ==================
``/account/v1.0/service/user_catalogs`` POST       Get 2 catalogs containing uuid to displayname mapping and the opposite
======================================= =========  ==================

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

Tokens API Operations
----------------------

Authenticate
^^^^^^^^^^^^

Fallback call which receives the user token or the user uuid/token pair and
returns back the token as well as information about the token holder and the
services he/she can access.

========================================= =========  ==================
Uri                                       Method     Description
========================================= =========  ==================
``/identity/v2.0/tokens/``                POST       Checks whether the provided token is valid and conforms with the provided uuid (if present) and returns back information about the user
========================================= =========  ==================

The input should be json formatted.

Example request:

::

    {
        "auth":{
            "token":{
                "id":"CDEe2k0T/HdiJWBMMbHyOA=="
            },
            "tenantName":"c18088be-16b1-4263-8180-043c54e22903"
        }
    }

or

::

    {
        "auth":{
            "passwordCredentials":{
                "username":"c18088be-16b1-4263-8180-043c54e22903",
                "password":"CDEe2k0T/HdiJWBMMbHyOA=="
            },
            "tenantName":"c18088be-16b1-4263-8180-043c54e22903"
        }
    }


The tenantName in the above requests is optional.

The response is json formatted unless it is requested otherwise via format
request parameter or Accept header.

Example json response:

::

    {"access": {
        "serviceCatalog": [
           {"SNF:uiURL": "https://node2.example.com/ui/",
            "endpoints": [{
                "publicURL": "https://object-store.example.synnefo.org/pithos/public/v2.0",
                "versionId": "v2.0"}],
            "endpoints_links": [],
            "name": "pithos_public",
            "type": "public"},
           {"SNF:uiURL": "https://node2.example.com/ui/",
            "endpoints": [{
                "publicURL": "https://object-store.example.synnefo.org/pithos/object-store/v1",
                "versionId": "v1"}],
            "endpoints_links": [],
            "name": "pithos_object-store",
            "type": "object-store"},
           {"SNF:uiURL": "https://node2.example.com/ui/",
            "endpoints": [{
                "publicURL": "https://object-store.example.synnefo.org/pithos/ui",
                "versionId": ""}],
            "endpoints_links": [],
            "name": "pithos_ui",
            "type": "pithos_ui"},
           {"SNF:uiURL": "http://localhost:8080",
            "endpoints": [{
                "publicURL": "https://accounts.example.synnefo.org/ui/v1.0",
                "versionId": "v1.0"}],
            "endpoints_links": [],
            "name": "astakos_ui",
            "type": "astakos_ui"},
           {"SNF:uiURL": "http://localhost:8080",
            "endpoints": [{
                "publicURL": "https://accounts.example.synnefo.org/account/v1.0",
                "versionId": "v1.0"}],
            "endpoints_links": [],
            "name": "astakos_account",
            "type": "account"},
           {"SNF:uiURL": "http://localhost:8080",
            "endpoints": [{
                "publicURL": "https://accounts.example.synnefo.org/identity/v2.0",
                "versionId": "v2.0"}],
            "endpoints_links": [],
            "name": "astakos_keystone",
            "type": "identity"}],
      "token": {
          "expires": "2013-06-19T15:23:59.975572+00:00",
           "id": "CDEe2k0T/HdiJWBMMbHyOA==",
           "tenant": {"id": "c18088be-16b1-4263-8180-043c54e22903",
            "name": "Firstname Lastname"}},
      "user": {
          "id": "c18088be-16b1-4263-8180-043c54e22903",
           "name": "Firstname Lastname",
           "roles": [{"id": 1, "name": "default"},
           "roles_links": []}}}

Example xml response:

::

    <?xml version="1.0" encoding="UTF-8"?>

    <access xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns="http://docs.openstack.org/identity/api/v2.0">
        <token id="CDEe2k0T/HdiJWBMMbHyOA==" expires="2013-06-19T15:23:59.975572+00:00">
            <tenant id="c18088be-16b1-4263-8180-043c54e22903" name="Firstname Lastname" />
        </token>
        <user id="c18088be-16b1-4263-8180-043c54e22903" name="Firstname Lastname">
            <roles>
                    <role id="1" name="default"/>
            </roles>
        </user>
        <serviceCatalog>
            <service type="public" name="pithos_public" SNF:uiURL="">
                    <endpoint
                            versionId="v2.0"
                            publicURL="https://object-store.example.synnefo.org/pithos/public/v2.0"
            </service>
            <service type="object-store" name="pithos_object-store" SNF:uiURL="">
                    <endpoint
                            versionId="v1"
                            publicURL="https://object-store.example.synnefo.org/pithos/object-store/v1"
            </service>
            <service type="pithos_ui" name="pithos_ui" SNF:uiURL="">
                    <endpoint
                            versionId=""
                            publicURL="https://object-store.example.synnefo.org/pithos/ui"
            </service>
            <service type="astakos_ui" name="astakos_ui" SNF:uiURL="">
                    <endpoint
                            versionId="v1.0"
                            publicURL="https://accounts.example.synnefo.org/ui/v1.0"
            </service>
            <service type="account" name="astakos_account" SNF:uiURL="">
                    <endpoint
                            versionId="v1.0"
                            publicURL="https://accounts.example.synnefo.org/account/v1.0"
            </service>
            <service type="identity" name="astakos_keystone" SNF:uiURL="">
                    <endpoint
                            versionId="v2.0"
                            publicURL="https://accounts.example.synnefo.org/identity/v2.0"
            </service>
        </serviceCatalog>
    </access>

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           Method not allowed or invalid request format or missing expected input
401 (Unauthorized)          Invalid token or invalid creadentials or tenantName does not comply with the provided token
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================



Get endpoints
^^^^^^^^^^^^^

Return a json (or xml) formatted dictionary containing information about registered endpoints

========================================= =========  ==================
Uri                                       Method     Description
========================================= =========  ==================
``/astakos/api/tokens/<token>/endpoints`` GET        Returns a list registered endpoints
========================================= =========  ==================

|

====================  ============================
Request Header Name   Value
====================  ============================
X-Auth-Token          User authentication token
====================  ============================

|

======================  ============================
Request Parameter Name  Value

======================  ============================
belongsTo               Check that the token belongs to a supplied user
marker                  Return endpoints (ordered by ID) whose ID is higher than the marker
limit                   Maximum number of endpoints to return
======================  ============================

|

Example json reply:

::

    {"endpoints": [
        {"name": "cyclades",
         "region": "cyclades",
         "internalURL": "https://node1.example.com/v1",
         "adminURL": "https://node1.example.com/v1",
         "type": null,
         "id": 5,
         "publicURL": "https://node1.example.com/vi/"},
        {"name": "pithos",
         "region": "pithos",
         "internalURL": "https://node2.example.com/vi/",
         "adminURL": "https://node2.example.com/v1",
         "type": null,
         "id": 6,
         "publicURL": "https://node2.example.com/vi/"},
    ],
    "endpoint_links": [{
        "href": "/astakos/api/tokens/0000/endpoints?marker=6&limit=10000",
         "rel": "next"}]}


Example xml reply:

::

    <?xml version="1.0" encoding="UTF-8"?>
    <endpoints xmlns="http://docs.openstack.org/identity/api/v2.0">
        <endpoint "name"="cyclades" "region"="cyclades" "internalURL"="https://node1.example.com/ui/" "adminURL"="https://node1.example.com/ui/" "id"="5" "publicURL"="https://node1.example.com/ui/" />
        <endpoint "name"="pithos" "region"="pithos" "internalURL"="https://node2.example.com/ui/" "adminURL"="https://node2.example.com/v1" "id"="6" "publicURL"="https://node2.example.com/ui/" />
    </endpoints>
    <endpoint_links>
            <endpoint_link "href"="/astakos/api/tokens/0000/endpoints?marker=6&amp;limit=10000" "rel"="next" />
    </endpoint_links>


|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           Method not allowed or token does not belong to the specific user
401 (Unauthorized)          Missing or expired or invalid service token
403 (Forbidden)             Path token does not comply with X-Auth-Token
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================
