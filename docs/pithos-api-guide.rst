Pithos API
==========

Introduction
------------

Pithos is a storage service implemented by GRNET (http://www.grnet.gr). Data is stored as objects, organized in containers, belonging to an account. This hierarchy of storage layers has been inspired by the OpenStack Object Storage (OOS) API and similar CloudFiles API by Rackspace. The Pithos API follows the OOS API as closely as possible. One of the design requirements has been to be able to use Pithos with clients built for the OOS, without changes.

However, to be able to take full advantage of the Pithos infrastructure, client software should be aware of the extensions that differentiate Pithos from OOS. Pithos objects can be updated, or appended to. Pithos will store sharing permissions per object and enforce corresponding authorization policies. Automatic version management, allows taking account and container listings back in time, as well as reading previous instances of objects.

The storage backend of Pithos is block oriented, permitting efficient, deduplicated data placement. The block structure of objects is exposed at the API layer, in order to encourage external software to implement advanced data management operations.

This document's goals are:

* Define the Pithos ReST API that allows the storage and retrieval of data and metadata via HTTP calls
* Specify metadata semantics and user interface guidelines for a common experience across client software implementations

The present document is meant to be read alongside the OOS API documentation. Thus, it is suggested that the reader is familiar with associated technologies, the OOS API as well as the first version of the Pithos API. This document refers to the second version of Pithos. Information on the first version of the storage API can be found at http://code.google.com/p/gss.

Whatever marked as to be determined (**TBD**), should not be considered by implementors.

More info about Pithos can be found here: https://code.grnet.gr/projects/pithos

Document Revisions
^^^^^^^^^^^^^^^^^^

=========================  ================================
Revision                   Description
=========================  ================================
0.13 (Mar 27, 2013)        Restrict public object listing only to the owner.
                           Do not propagate public URL information in shared objects.
0.13 (Jan 21, 2013)        Proxy identity management services
\                          UUID to displayname translation
0.9 (Feb 17, 2012)         Change permissions model.
0.10 (Jul 18, 2012)        Support for bulk COPY/MOVE/DELETE
\                          Optionally include public objects in listings.
0.9 (Feb 17, 2012)         Change permissions model.
\                          Do not include user-defined metadata in account/container/object listings.
0.8 (Jan 24, 2012)         Update allowed versioning values.
\                          Change policy/meta formatting in JSON/XML replies.
\                          Document that all non-ASCII characters in headers should be URL-encoded.
\                          Support metadata-based queries when listing objects at the container level.
\                          Note Content-Type issue when using the internal django web server.
\                          Add object UUID field.
\                          Always reply with the MD5 in the ETag.
\                          Note that ``/login`` will only work if an external authentication system is defined.
\                          Include option to ignore Content-Type on ``COPY``/``MOVE``.
\                          Use format parameter for conflict (409) and uploaded hash list (container level) replies.
0.7 (Nov 21, 2011)         Suggest upload/download methods using hashmaps.
\                          Propose syncing algorithm.
\                          Support cross-account object copy and move.
\                          Pass token as a request parameter when using ``POST`` via an HTML form.
\                          Optionally use source account to update object from another object.
\                          Use container ``POST`` to upload missing blocks of data.
\                          Report policy in account headers.
\                          Add insufficient quota reply.
\                          Use special meta to always report Merkle hash.
0.6 (Sept 13, 2011)        Reply with Merkle hash as the ETag when updating objects.
\                          Include version id in object replace/change replies.
\                          Change conflict (409) replies format to text.
\                          Tags should be migrated to a meta value.
\                          Container ``PUT`` updates metadata/policy.
\                          Report allowed actions in shared object replies.
\                          Provide ``https://hostname/login`` for Shibboleth authentication.
\                          Use ``hashmap`` parameter in object ``GET``/``PUT`` to use hashmaps.
0.5 (July 22, 2011)        Object update from another object's data.
\                          Support object truncate.
\                          Create object using a standard HTML form.
\                          Purge container/object history.
\                          List other accounts that share objects with a user.
\                          List shared containers/objects.
\                          Update implementation guidelines.
\                          Check preconditions when creating/updating objects.
0.4 (July 01, 2011)        Object permissions and account groups.
\                          Control versioning behavior and container quotas with container policy directives.
\                          Support updating/deleting individual metadata with ``POST``.
\                          Create object using hashmap.
0.3 (June 14, 2011)        Large object support with ``X-Object-Manifest``.
\                          Allow for publicly available objects via ``https://hostname/public``.
\                          Support time-variant account/container listings.
\                          Add source version when duplicating with ``PUT``/``COPY``.
\                          Request version in object ``HEAD``/``GET`` requests (list versions with ``GET``).
0.2 (May 31, 2011)         Add object meta listing and filtering in containers.
\                          Include underlying storage characteristics in container meta.
\                          Support for partial object updates through ``POST``.
\                          Expose object hashmaps through ``GET``.
\                          Support for multi-range object ``GET`` requests.
0.1 (May 17, 2011)         Initial release. Based on OpenStack Object Storage Developer Guide API v1 (Apr. 15, 2011).
=========================  ================================

Pithos Users and Authentication
-------------------------------

In Pithos, each user is uniquely identified by a token. All API requests require a token and each token is internally resolved to an account string. The API uses the account string to identify the user's own files, thus whether a request is local or cross-account.

Pithos does not keep a user database. For development and testing purposes, user identifiers and their corresponding tokens can be defined in the settings file. However, Pithos is designed with an external authentication service in mind. This service must handle the details of validating user credentials and communicate with Pithos via a middleware software component that, given a token, fills in the internal request account variable.

Client software using Pithos, if not already knowing a user's identifier and token, should forward to the ``/login`` URI. The Pithos server, depending on its configuration will redirect to the appropriate login page.

The login URI accepts the following parameters:

======================  =========================
Request Parameter Name  Value
======================  =========================
next                    The URI to redirect to when the process is finished
renew                   Force token renewal (no value parameter)
force                   Force logout current user (no value parameter)
======================  =========================

When done with logging in, the service's login URI should redirect to the URI provided with ``next``, adding ``user`` and ``token`` parameters, which contain the account and token fields respectively.

A user management service that implements a login URI according to these conventions is Astakos (https://code.grnet.gr/projects/astakos), by GRNET.

User feedback
-------------

Client software using Pithos, should forward to the ``/feedback`` URI. The Pithos service, depending on its configuration will delegate the request to the appropriate identity management URI.

============================ =========  ==================
Uri                          Method     Description
============================ =========  ==================
``/pithos/astakos/feedback`` POST       Send feedback
============================ =========  ==================

|

======================  =========================
Request Parameter Name  Value
======================  =========================
feedback_msg            Feedback message
feedback_data           Additional information about service client status
======================  =========================

|

====================  ===========================
Request Header Name   Value
====================  ===========================
X-Auth-Token          User authentication token
====================  ===========================

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

User translation catalogs
-------------------------

Client software using Pithos, should forward to the ``/user_catalogs`` URI to get uuid to displayname translations and vice versa. The Pithos service, depending on its configuration will delegate the request to the appropriate identity management URI.

================================= =========  ==================
Uri                               Method     Description
================================= =========  ==================
``/pithos/astakos/user_catalogs`` POST       Get 2 catalogs containing uuid to displayname mapping and the opposite
================================= =========  ==================

|

====================  ===========================
Request Header Name   Value
====================  ===========================
X-Auth-Token          User authentication token
====================  ===========================

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

The Pithos API
--------------

The URI requests supported by the Pithos API follow one of the following forms:

* Top level: ``https://hostname/v1/``
* Account level: ``https://hostname/v1/<account>``
* Container level: ``https://hostname/v1/<account>/<container>``
* Object level: ``https://hostname/v1/<account>/<container>/<object>``

All requests must include an ``X-Auth-Token`` - as a header, or a parameter.

The allowable request operations and respective return codes per level are presented in the remainder of this chapter. Common to all requests are the following return codes.

==============================  ================================
Return Code                     Description
==============================  ================================
400 (Bad Request)               The request is invalid
401 (Unauthorized)              Missing or invalid token
403 (Forbidden)                 Request not allowed
404 (Not Found)                 The requested resource was not found
413 (Request Entity Too Large)  Insufficient quota to complete the request
503 (Service Unavailable)       The request cannot be completed because of an internal error
==============================  ================================

Top Level
^^^^^^^^^

List of operations:

=========  ==================
Operation  Description
=========  ==================
GET        Authentication (for compatibility with the OOS API) or list allowed accounts
=========  ==================

GET
"""

If the ``X-Auth-User`` and ``X-Auth-Key`` headers are given, a dummy ``X-Auth-Token`` and ``X-Storage-Url`` will be replied, which can be used as a guest token/namespace for testing Pithos.

================  =====================
Return Code       Description
================  =====================
204 (No Content)  The request succeeded
================  =====================

If an ``X-Auth-Token`` is already present, the operation will be interpreted as a request to list other accounts that share objects to the user.

======================  =========================
Request Parameter Name  Value
======================  =========================
limit                   The amount of results requested (default is 10000)
marker                  Return containers with name lexicographically after marker
format                  Optional extended reply type (can be ``json`` or ``xml``)
======================  =========================

The reply is a list of account names.
If a ``format=xml`` or ``format=json`` argument is given, extended information on the accounts will be returned, serialized in the chosen format.
For each account, the information will include the following (names will be in lower case and with hyphens replaced with underscores):

===========================  ============================
Name                         Description
===========================  ============================
name                         The name of the account
last_modified                The last account modification date (regardless of ``until``)
===========================  ============================

Example ``format=json`` reply:

::

  [{"name": "user-uuid", "last_modified": "2011-12-02T08:10:41.565891+00:00"}, ...]

Example ``format=xml`` reply:

::

  <?xml version="1.0" encoding="UTF-8"?>
  <accounts>
    <account>
      <name>user-uuid</name>
      <last_modified>2011-12-02T08:10:41.565891+00:00</last_modified>
    </account>
    <account>...</account>
  </accounts>

===========================  =====================
Return Code                  Description
===========================  =====================
200 (OK)                     The request succeeded
204 (No Content)             The user has no access to other accounts (only for non-extended replies)
===========================  =====================

Will use a ``200`` return code if the reply is of type JSON/XML.

Account Level
^^^^^^^^^^^^^

List of operations:

=========  ==================
Operation  Description
=========  ==================
HEAD       Retrieve account metadata
GET        List containers
POST       Update account metadata
=========  ==================

HEAD
""""

====================  ===========================
Request Header Name   Value
====================  ===========================
If-Modified-Since     Retrieve if account has changed since provided timestamp
If-Unmodified-Since   Retrieve if account has not changed since provided timestamp
====================  ===========================

|

======================  ===================================
Request Parameter Name  Value
======================  ===================================
until                   Optional timestamp
======================  ===================================

Cross-user requests are not allowed to use ``until`` and only include the account modification date in the reply.

==========================  =====================
Reply Header Name           Value
==========================  =====================
X-Account-Container-Count   The total number of containers
X-Account-Bytes-Used        The total number of bytes stored
X-Account-Until-Timestamp   The last account modification date until the timestamp provided
X-Account-Group-*           Optional user defined groups
X-Account-Policy-*          Account behavior and limits
X-Account-Meta-*            Optional user defined metadata
Last-Modified               The last account modification date (regardless of ``until``)
==========================  =====================

|

================  =====================
Return Code       Description
================  =====================
204 (No Content)  The request succeeded
================  =====================


GET
"""

====================  ===========================
Request Header Name   Value
====================  ===========================
If-Modified-Since     Retrieve if account has changed since provided timestamp
If-Unmodified-Since   Retrieve if account has not changed since provided timestamp
====================  ===========================

|

======================  =========================
Request Parameter Name  Value
======================  =========================
limit                   The amount of results requested (default is 10000)
marker                  Return containers with name lexicographically after marker
format                  Optional extended reply type (can be ``json`` or ``xml``)
shared                  Show only shared containers (no value parameter)
public                  Show only public containers (no value parameter / avalaible only for owner requests)
until                   Optional timestamp
======================  =========================

The reply is a list of container names. Account headers (as in a ``HEAD`` request) will also be included.
Cross-user requests are not allowed to use ``until`` and only include the account/container modification dates in the reply.

If a ``format=xml`` or ``format=json`` argument is given, extended information on the containers will be returned, serialized in the chosen format.
For each container, the information will include all container metadata, except user-defined (names will be in lower case and with hyphens replaced with underscores):

===========================  ============================
Name                         Description
===========================  ============================
name                         The name of the container
count                        The number of objects inside the container
bytes                        The total size of the objects inside the container
last_modified                The last container modification date (regardless of ``until``)
x_container_until_timestamp  The last container modification date until the timestamp provided
x_container_policy           Container behavior and limits
===========================  ============================

Example ``format=json`` reply:

::

  [{"name": "pithos",
    "bytes": 62452,
    "count": 8374,
    "last_modified": "2011-12-02T08:10:41.565891+00:00",
    "x_container_policy": {"quota": "53687091200", "versioning": "auto"}}, ...]

Example ``format=xml`` reply:

::

  <?xml version="1.0" encoding="UTF-8"?>
  <account name="user-uuid">
    <container>
      <name>pithos</name>
      <bytes>62452</bytes>
      <count>8374</count>
      <last_modified>2011-12-02T08:10:41.565891+00:00</last_modified>
      <x_container_policy>
        <key>quota</key><value>53687091200</value>
        <key>versioning</key><value>auto</value>
      </x_container_policy>
    </container>
    <container>...</container>
  </account>

For more examples of container details returned in JSON/XML formats refer to the OOS API documentation. In addition to the OOS API, Pithos returns policy fields, grouped as key-value pairs.

===========================  =====================
Return Code                  Description
===========================  =====================
200 (OK)                     The request succeeded
204 (No Content)             The account has no containers (only for non-extended replies)
304 (Not Modified)           The account has not been modified
412 (Precondition Failed)    The condition set can not be satisfied
===========================  =====================

Will use a ``200`` return code if the reply is of type JSON/XML.


POST
""""

====================  ===========================
Request Header Name   Value
====================  ===========================
X-Account-Group-*     Optional user defined groups
X-Account-Meta-*      Optional user defined metadata
====================  ===========================

|

======================  ============================================
Request Parameter Name  Value
======================  ============================================
update                  Do not replace metadata/groups (no value parameter)
======================  ============================================

No reply content/headers.

The operation will overwrite all user defined metadata, except if ``update`` is defined.
To create a group, include an ``X-Account-Group-*`` header with the name in the key and a comma separated list of user identifiers in the value. If no ``X-Account-Group-*`` header is present, no changes will be applied to groups. The ``update`` parameter also applies to groups. To delete a specific group, use ``update`` and an empty header value.

================  ===============================
Return Code       Description
================  ===============================
202 (Accepted)    The request has been accepted
================  ===============================


Container Level
^^^^^^^^^^^^^^^

List of operations:

=========  ============================
Operation  Description
=========  ============================
HEAD       Retrieve container metadata
GET        List objects
PUT        Create/update container
POST       Update container metadata
DELETE     Delete container
=========  ============================


HEAD
""""

====================  ===========================
Request Header Name   Value
====================  ===========================
If-Modified-Since     Retrieve if container has changed since provided timestamp
If-Unmodified-Since   Retrieve if container has not changed since provided timestamp
====================  ===========================

|

======================  ===================================
Request Parameter Name  Value
======================  ===================================
until                   Optional timestamp
======================  ===================================

Cross-user requests are not allowed to use ``until`` and only include the container modification date in the reply.

===========================  ===============================
Reply Header Name            Value
===========================  ===============================
X-Container-Object-Count     The total number of objects in the container
X-Container-Bytes-Used       The total number of bytes of all objects stored
X-Container-Block-Size       The block size used by the storage backend
X-Container-Block-Hash       The hash algorithm used for block identifiers in object hashmaps
X-Container-Until-Timestamp  The last container modification date until the timestamp provided
X-Container-Object-Meta      A list with all meta keys used by objects (**TBD**)
X-Container-Policy-*         Container behavior and limits
X-Container-Meta-*           Optional user defined metadata
Last-Modified                The last container modification date (regardless of ``until``)
===========================  ===============================

The keys returned in ``X-Container-Object-Meta`` are all the unique strings after the ``X-Object-Meta-`` prefix, formatted as a comma-separated list. See container ``PUT`` for a reference of policy directives. (**TBD**)

================  ===============================
Return Code       Description
================  ===============================
204 (No Content)  The request succeeded
================  ===============================


GET
"""

====================  ===========================
Request Header Name   Value
====================  ===========================
If-Modified-Since     Retrieve if container has changed since provided timestamp
If-Unmodified-Since   Retrieve if container has not changed since provided timestamp
====================  ===========================

|

======================  ===================================
Request Parameter Name  Value
======================  ===================================
limit                   The amount of results requested (default is 10000)
marker                  Return containers with name lexicographically after marker
prefix                  Return objects starting with prefix
delimiter               Return objects up to the delimiter (discussion follows)
path                    Assume ``prefix=path`` and ``delimiter=/``
format                  Optional extended reply type (can be ``json`` or ``xml``)
meta                    Return objects that satisfy the key queries in the specified comma separated list (use ``<key>``, ``!<key>`` for existence queries, ``<key><op><value>`` for value queries, where ``<op>`` can be one of ``=``, ``!=``, ``<=``, ``>=``, ``<``, ``>``)
shared                  Show only objects (no value parameter)
public                  Show only public objects (no value parameter / avalaible only for owner reqeusts)
until                   Optional timestamp
======================  ===================================

The ``path`` parameter overrides ``prefix`` and ``delimiter``. When using ``path``, results will include objects ending in ``delimiter``.

The keys given with ``meta`` will be matched with the strings after the ``X-Object-Meta-`` prefix.

The reply is a list of object names. Container headers (as in a ``HEAD`` request) will also be included.
Cross-user requests are not allowed to use ``until`` and include the following limited set of headers in the reply:

===========================  ===============================
Reply Header Name            Value
===========================  ===============================
X-Container-Block-Size       The block size used by the storage backend
X-Container-Block-Hash       The hash algorithm used for block identifiers in object hashmaps
X-Container-Object-Meta      A list with all meta keys used by allowed objects (**TBD**)
Last-Modified                The last container modification date
===========================  ===============================

If a ``format=xml`` or ``format=json`` argument is given, extended information on the objects will be returned, serialized in the chosen format.
For each object, the information will include all object metadata, except user-defined (names will be in lower case and with hyphens replaced with underscores). User-defined metadata includes ``X-Object-Meta-*``, ``X-Object-Manifest``, ``Content-Disposition`` and ``Content-Encoding`` keys. Also, sharing directives will only be included with the actual shared objects (inherited permissions are not calculated):

==========================  ======================================
Name                        Description
==========================  ======================================
name                        The name of the object
hash                        The ETag of the object
bytes                       The size of the object
content_type                The MIME content type of the object
last_modified               The last object modification date (regardless of version)
x_object_hash               The Merkle hash
x_object_uuid               The object's UUID
x_object_version            The object's version identifier
x_object_version_timestamp  The object's version timestamp
x_object_modified_by        The user that committed the object's version
x_object_sharing            Object permissions (optional)
x_object_allowed_to         Allowed actions on object (optional)
x_object_public             Object's publicly accessible URI (optional: present if the object is public and the request user is the object owner)
==========================  ======================================

Sharing metadata and last modification timestamp will only be returned if there is no ``until`` parameter defined.

Extended replies may also include virtual directory markers in separate sections of the ``json`` or ``xml`` results.
Virtual directory markers are only included when ``delimiter`` is explicitly set. They correspond to the substrings up to and including the first occurrence of the delimiter.
In JSON results they appear as dictionaries with only a ``subdir`` key. In XML results they appear interleaved with ``<object>`` tags as ``<subdir name="..." />``.
In case there is an object with the same name as a virtual directory marker, the object will be returned.

Example ``format=json`` reply:

::

  [{"name": "object",
    "bytes": 0,
    "hash": "d41d8cd98f00b204e9800998ecf8427e",
    "content_type": "application/octet-stream",
    "last_modified": "2011-12-02T08:10:41.565891+00:00",
    "x_object_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "x_object_uuid": "8ed9af1b-c948-4bb6-82b0-48344f5c822c",
    "x_object_version": 98,
    "x_object_version_timestamp": "1322813441.565891",
    "x_object_modified_by": "user-uuid"}, ...]

Example ``format=xml`` reply:

::

  <?xml version="1.0" encoding="UTF-8"?>
  <container name="pithos">
    <object>
      <name>object</name>
      <bytes>0</bytes>
      <hash>d41d8cd98f00b204e9800998ecf8427e</hash>
      <content_type>application/octet-stream</content_type>
      <last_modified>2011-12-02T08:10:41.565891+00:00</last_modified>
      <x_object_hash>e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</x_object_hash>
      <x_object_uuid>8ed9af1b-c948-4bb6-82b0-48344f5c822c</x_object_uuid>
      <x_object_version>98</x_object_version>
      <x_object_version_timestamp>1322813441.565891</x_object_version_timestamp>
      <x_object_modified_by>user-uuid</x_object_modified_by>
    </object>
    <object>...</object>
  </container>

For more examples of container details returned in JSON/XML formats refer to the OOS API documentation. In addition to the OOS API, Pithos returns more fields that should help with synchronization.

===========================  ===============================
Return Code                  Description
===========================  ===============================
200 (OK)                     The request succeeded
204 (No Content)             The account has no containers (only for non-extended replies)
304 (Not Modified)           The container has not been modified
412 (Precondition Failed)    The condition set can not be satisfied
===========================  ===============================

Will use a ``200`` return code if the reply is of type JSON/XML.


PUT
"""

====================  ================================
Request Header Name   Value
====================  ================================
X-Container-Policy-*  Container behavior and limits
X-Container-Meta-*    Optional user defined metadata
====================  ================================
 
No reply content/headers.

If no policy is defined, the container will be created with the default values.
Available policy directives:

* ``versioning``: Set to ``auto`` or ``none`` (default is ``auto``)
* ``quota``: Size limit in KB (default is ``0`` - unlimited)

If the container already exists, the operation is equal to a ``POST`` with ``update`` defined.

================  ===============================
Return Code       Description
================  ===============================
201 (Created)     The container has been created
202 (Accepted)    The request has been accepted
================  ===============================


POST
""""

====================  ================================
Request Header Name   Value
====================  ================================
Content-Length        The size of the supplied data (optional, to upload)
Content-Type          The MIME content type of the supplied data (optional, to upload)
Transfer-Encoding     Set to ``chunked`` to specify incremental uploading (if used, ``Content-Length`` is ignored)
X-Container-Policy-*  Container behavior and limits
X-Container-Meta-*    Optional user defined metadata
====================  ================================

|

======================  ============================================
Request Parameter Name  Value
======================  ============================================
format                  Optional hash list reply type (can be ``json`` or ``xml``)
update                  Do not replace metadata/policy (no value parameter)
======================  ============================================

No reply content/headers, except when uploading data, where the reply consists of a list of hashes for the blocks received (in the format specified).

The operation will overwrite all user defined metadata, except if ``update`` is defined.
To change policy, include an ``X-Container-Policy-*`` header with the name in the key. If no ``X-Container-Policy-*`` header is present, no changes will be applied to policy. The ``update`` parameter also applies to policy - deleted values will revert to defaults. To delete/revert a specific policy directive, use ``update`` and an empty header value. See container ``PUT`` for a reference of policy directives.

To upload blocks of data to the container, set ``Content-Type`` to ``application/octet-stream`` and ``Content-Length`` to a valid value (except if using ``chunked`` as the ``Transfer-Encoding``).

================  ===============================
Return Code       Description
================  ===============================
202 (Accepted)    The request has been accepted
================  ===============================


DELETE
""""""

======================  ===================================
Request Parameter Name  Value
======================  ===================================
until                   Optional timestamp
delimiter               Optional delete objects starting with container name and delimiter
======================  ===================================

If ``until`` is defined, the container is "purged" up to that time (the history of all objects up to then is deleted). If also ``delimiter`` is defined, purge is applied only on the container.

No reply content/headers.

================  ===============================
Return Code       Description
================  ===============================
204 (No Content)  The request succeeded
409 (Conflict)    The container is not empty
================  ===============================


Object Level
^^^^^^^^^^^^

List of operations:

=========  =================================
Operation  Description
=========  =================================
HEAD       Retrieve object metadata
GET        Read object data
PUT        Write object data or copy/move object
COPY       Copy object
MOVE       Move object
POST       Update object metadata/data
DELETE     Delete object
=========  =================================


HEAD
""""

====================  ================================
Request Header Name   Value
====================  ================================
If-Match              Retrieve if ETags match
If-None-Match         Retrieve if ETags don't match
If-Modified-Since     Retrieve if object has changed since provided timestamp
If-Unmodified-Since   Retrieve if object has not changed since provided timestamp
====================  ================================

|

======================  ===================================
Request Parameter Name  Value
======================  ===================================
version                 Optional version identifier
======================  ===================================

|

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
ETag                        The ETag of the object
Content-Length              The size of the object
Content-Type                The MIME content type of the object
Last-Modified               The last object modification date (regardless of version)
Content-Encoding            The encoding of the object (optional)
Content-Disposition         The presentation style of the object (optional)
X-Object-Hash               The Merkle hash
X-Object-UUID               The object's UUID
X-Object-Version            The object's version identifier
X-Object-Version-Timestamp  The object's version timestamp
X-Object-Modified-By        The user that comitted the object's version
X-Object-Manifest           Object parts prefix in ``<container>/<object>`` form (optional)
X-Object-Sharing            Object permissions (optional)
X-Object-Shared-By          Object inheriting permissions (optional)
X-Object-Allowed-To         Allowed actions on object (optional)
X-Object-Public             Object's publicly accessible URI (optional: present if the object is public and the request user is the object owner)
X-Object-Meta-*             Optional user defined metadata
==========================  ===============================

|

================  ===============================
Return Code       Description
================  ===============================
200 (No Content)  The request succeeded
================  ===============================


GET
"""

====================  ================================
Request Header Name   Value
====================  ================================
Range                 Optional range of data to retrieve
If-Range              Retrieve the missing part if entity is unchanged; otherwise, retrieve the entire new entity (used together with Range header)
If-Match              Retrieve if ETags match
If-None-Match         Retrieve if ETags don't match
If-Modified-Since     Retrieve if object has changed since provided timestamp
If-Unmodified-Since   Retrieve if object has not changed since provided timestamp
====================  ================================

|

======================  ===================================
Request Parameter Name  Value
======================  ===================================
format                  Optional extended reply type (can be ``json`` or ``xml``)
hashmap                 Optional request for hashmap (no value parameter)
version                 Optional version identifier or ``list`` (specify a format if requesting a list)
======================  ===================================

The reply is the object's data (or part of it), except if a hashmap is requested with ``hashmap``, or a version list with ``version=list`` (in both cases an extended reply format must be specified). Object headers (as in a ``HEAD`` request) are always included.

Hashmaps expose the underlying storage format of the object. Note that each hash is computed after trimming trailing null bytes of the corresponding block. The ``X-Object-Hash`` header reports the single Merkle hash of the object's hashmap (refer to http://bittorrent.org/beps/bep_0030.html for more information).

Example ``format=json`` reply:

::

  {"block_hash": "sha1", "hashes": ["7295c41da03d7f916440b98e32c4a2a39351546c", ...], "block_size": 131072, "bytes": 242}

Example ``format=xml`` reply:

::

  <?xml version="1.0" encoding="UTF-8"?>
  <object name="file" bytes="24223726" block_size="131072" block_hash="sha1">
    <hash>7295c41da03d7f916440b98e32c4a2a39351546c</hash>
    <hash>...</hash>
  </object>

Version lists include the version identifier and timestamp for each available object version. Version identifiers can be arbitrary strings, so use the timestamp to find newer versions.

Example ``format=json`` reply:

::

  {"versions": [[85, "1322734861.248469"], [86, "1322734905.009272"], ...]}

Example ``format=xml`` reply:

::

  <?xml version="1.0" encoding="UTF-8"?>
  <object name="file">
    <version timestamp="1322734861.248469">85</version>
    <version timestamp="1322734905.009272">86</version>
    <version timestamp="...">...</version>
  </object>

The ``Range`` header may include multiple ranges, as outlined in RFC2616. Then the ``Content-Type`` of the reply will be ``multipart/byteranges`` and each part will include a ``Content-Range`` header.

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
ETag                        The ETag of the object
Content-Length              The size of the data returned
Content-Type                The MIME content type of the object
Content-Range               The range of data included (only on a single range request)
Last-Modified               The last object modification date (regardless of version)
Content-Encoding            The encoding of the object (optional)
Content-Disposition         The presentation style of the object (optional)
X-Object-Hash               The Merkle hash
X-Object-UUID               The object's UUID
X-Object-Version            The object's version identifier
X-Object-Version-Timestamp  The object's version timestamp
X-Object-Modified-By        The user that comitted the object's version
X-Object-Manifest           Object parts prefix in ``<container>/<object>`` form (optional)
X-Object-Sharing            Object permissions (optional)
X-Object-Shared-By          Object inheriting permissions (optional)
X-Object-Allowed-To         Allowed actions on object (optional)
X-Object-Public             Object's publicly accessible URI (optional: present if the object is public and the request user is the object owner)
X-Object-Meta-*             Optional user defined metadata
==========================  ===============================

Sharing headers (``X-Object-Sharing``, ``X-Object-Shared-By`` and ``X-Object-Allowed-To``) are only included if the request is for the object's latest version (no specific ``version`` parameter is set).

===========================  ==============================
Return Code                  Description
===========================  ==============================
200 (OK)                     The request succeeded
206 (Partial Content)        The range request succeeded
304 (Not Modified)           The object has not been modified
412 (Precondition Failed)    The condition set can not be satisfied
416 (Range Not Satisfiable)  The requested range is out of limits
===========================  ==============================


PUT
"""

====================  ================================
Request Header Name   Value
====================  ================================
If-Match              Put if ETags match with current object
If-None-Match         Put if ETags don't match with current object
ETag                  The MD5 hash of the object (optional to check written data)
Content-Length        The size of the data written
Content-Type          The MIME content type of the object
Transfer-Encoding     Set to ``chunked`` to specify incremental uploading (if used, ``Content-Length`` is ignored)
X-Copy-From           The source path in the form ``/<container>/<object>``
X-Move-From           The source path in the form ``/<container>/<object>``
X-Source-Account      The source account to copy/move from
X-Source-Version      The source version to copy from
Content-Encoding      The encoding of the object (optional)
Content-Disposition   The presentation style of the object (optional)
X-Object-Manifest     Object parts prefix in ``<container>/<object>`` form (optional)
X-Object-Sharing      Object permissions (optional)
X-Object-Public       Object is publicly accessible (optional)
X-Object-Meta-*       Optional user defined metadata
====================  ================================

|

======================  ===================================
Request Parameter Name  Value
======================  ===================================
format                  Optional extended request/conflict response type (can be ``json`` or ``xml``)
hashmap                 Optional hashmap provided instead of data (no value parameter)
delimiter               Optional copy/move objects starting with object's path and delimiter (to be used with X-Copy-From/X-Move-From)
======================  ===================================

The request is the object's data (or part of it), except if a hashmap is provided (using ``hashmap`` and ``format`` parameters). If using a hashmap and all different parts are stored in the server, the object is created. Otherwise the server returns Conflict (409) with the list of the missing parts (in simple text format, with one hash per line, or in JSON/XML - depending on the ``format`` parameter).

Hashmaps should be formatted as outlined in ``GET``.

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
ETag                        The MD5 hash of the object
X-Object-Version            The object's new version
==========================  ===============================

The ``X-Object-Sharing`` header may include either a ``read=...`` comma-separated user/group list, or a ``write=...`` comma-separated user/group list, or both separated by a semicolon (``;``). Groups are specified as ``<account>:<group>``. To publish the object, set ``X-Object-Public`` to ``true``. To unpublish, set to ``false``, or use an empty header value.

==============================  ==============================
Return Code                     Description
==============================  ==============================
201 (Created)                   The object has been created
409 (Conflict)                  The object can not be created from the provided hashmap (a list of missing hashes will be included in the reply)
411 (Length Required)           Missing ``Content-Length`` or ``Content-Type`` in the request
413 (Request Entity Too Large)  Insufficient quota to complete the request
422 (Unprocessable Entity)      The MD5 checksum of the data written to the storage system does not match the (optionally) supplied ETag value
==============================  ==============================


COPY
""""

====================  ================================
Request Header Name   Value
====================  ================================
If-Match              Proceed if ETags match with object
If-None-Match         Proceed if ETags don't match with object
Destination           The destination path in the form ``/<container>/<object>``
Destination-Account   The destination account to copy to
Content-Type          The MIME content type of the object (optional :sup:`*`)
Content-Encoding      The encoding of the object (optional)
Content-Disposition   The presentation style of the object (optional)
X-Source-Version      The source version to copy from
X-Object-Manifest     Object parts prefix in ``<container>/<object>`` form (optional)
X-Object-Sharing      Object permissions (optional)
X-Object-Public       Object is publicly accessible (optional)
X-Object-Meta-*       Optional user defined metadata
====================  ================================

:sup:`*` *When using django locally with the supplied web server, use the ignore_content_type parameter, or do provide a valid Content-Type, as a type of text/plain is applied by default to all requests. Client software should always state ignore_content_type, except when a Content-Type is explicitly defined by the user.*

======================  ===================================
Request Parameter Name  Value
======================  ===================================
format                  Optional conflict response type (can be ``json`` or ``xml``)
ignore_content_type     Ignore the supplied Content-Type
delimiter               Optional copy objects starting with object's path and delimiter
======================  ===================================

Refer to ``PUT``/``POST`` for a description of request headers. Metadata is also copied, updated with any values defined. Sharing/publishing options are not copied.

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
X-Object-Version            The object's new version
==========================  ===============================

|

==============================  ==============================
Return Code                     Description
==============================  ==============================
201 (Created)                   The object has been created
413 (Request Entity Too Large)  Insufficient quota to complete the request
==============================  ==============================


MOVE
""""

Same as ``COPY``, without the ``X-Source-Version`` request header. The ``MOVE`` operation is always applied on the latest version.


POST
""""

====================  ================================
Request Header Name   Value
====================  ================================
If-Match              Proceed if ETags match with object
If-None-Match         Proceed if ETags don't match with object
Content-Length        The size of the data written (optional, to update)
Content-Type          The MIME content type of the object (optional, to update)
Content-Range         The range of data supplied (optional, to update)
Transfer-Encoding     Set to ``chunked`` to specify incremental uploading (if used, ``Content-Length`` is ignored)
Content-Encoding      The encoding of the object (optional)
Content-Disposition   The presentation style of the object (optional)
X-Source-Object       Update with data from the object at path ``/<container>/<object>`` (optional, to update)
X-Source-Account      The source account to update from
X-Source-Version      The source version to update from (optional, to update)
X-Object-Bytes        The updated object's final size (optional, when updating)
X-Object-Manifest     Object parts prefix in ``<container>/<object>`` form (optional)
X-Object-Sharing      Object permissions (optional)
X-Object-Public       Object is publicly accessible (optional)
X-Object-Meta-*       Optional user defined metadata
====================  ================================

|

======================  ============================================
Request Parameter Name  Value
======================  ============================================
format                  Optional conflict response type (can be ``json`` or ``xml``)
update                  Do not replace metadata (no value parameter)
======================  ============================================

The ``Content-Encoding``, ``Content-Disposition``, ``X-Object-Manifest`` and ``X-Object-Meta-*`` headers are considered to be user defined metadata. An operation without the ``update`` parameter will overwrite all previous values and remove any keys not supplied. When using ``update`` any metadata with an empty value will be deleted.

To change permissions, include an ``X-Object-Sharing`` header (as defined in ``PUT``). To publish, include an ``X-Object-Public`` header, with a value of ``true``. If no such headers are defined, no changes will be applied to sharing/public. Use empty values to remove permissions/unpublish (unpublishing also works with ``false`` as a header value). Sharing options are applied to the object - not its versions.

To update an object's data:

* Either set ``Content-Type`` to ``application/octet-stream``, or provide an object with ``X-Source-Object``. If ``Content-Type`` has some other value, it will be ignored and only the metadata will be updated.
* If the data is supplied in the request (using ``Content-Type`` instead of ``X-Source-Object``), a valid ``Content-Length`` header is required - except if using chunked transfers (set ``Transfer-Encoding`` to ``chunked``).
* Set ``Content-Range`` as specified in RFC2616, with the following differences:

  * Client software MAY omit ``last-byte-pos`` of if the length of the range being transferred is unknown or difficult to determine.
  * Client software SHOULD not specify the ``instance-length`` (use a ``*``), unless there is a reason for performing a size check at the server.
* If ``Content-Range`` used has a ``byte-range-resp-spec = *``, data will be appended to the object.

Optionally, truncate the updated object to the desired length with the ``X-Object-Bytes`` header.

A data update will trigger an ETag change. Updated ETags may happen asynchronously and appear at the server with a delay.

No reply content. No reply headers if only metadata is updated.

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
ETag                        The new ETag of the object (data updated)
X-Object-Version            The object's new version
==========================  ===============================

|

==============================  ==============================
Return Code                     Description
==============================  ==============================
202 (Accepted)                  The request has been accepted (not a data update)
204 (No Content)                The request succeeded (data updated)
411 (Length Required)           Missing ``Content-Length`` in the request
413 (Request Entity Too Large)  Insufficient quota to complete the request
416 (Range Not Satisfiable)     The supplied range is invalid
==============================  ==============================

The ``POST`` method can also be used for creating an object via a standard HTML form. If the request ``Content-Type`` is ``multipart/form-data``, none of the above headers will be processed. The form should have an ``X-Object-Data`` field, as in the following example. The token is passed as a request parameter. ::

  <form method="post" action="https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/folder/EXAMPLE.txt?X-Auth-Token=0000" enctype="multipart/form-data">
    <input type="file" name="X-Object-Data">
    <input type="submit">
  </form>

This will create/override the object with the given name, as if using ``PUT``. The ``Content-Type`` of the object will be set to the value of the corresponding header sent in the part of the request containing the data (usually, automatically handled by the browser). Metadata, sharing and other object attributes can not be set this way. The response will contain the object's ETag.

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
ETag                        The MD5 hash of the object
X-Object-Version            The object's new version
==========================  ===============================

|

==============================  ==============================
Return Code                     Description
==============================  ==============================
201 (Created)                   The object has been created
413 (Request Entity Too Large)  Insufficient quota to complete the request
==============================  ==============================


DELETE
""""""

======================  ===================================
Request Parameter Name  Value
======================  ===================================
until                   Optional timestamp
delimiter               Optional delete also objects starting with object's path and delimiter
======================  ===================================

If ``until`` is defined, the object is "purged" up to that time (the history up to then is deleted). If also ``delimiter`` is defined, purge is applied only on the object.

No reply content/headers.

===========================  ==============================
Return Code                  Description
===========================  ==============================
204 (No Content)             The request succeeded
===========================  ==============================

Sharing and Public Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^

Read and write control in Pithos is managed by setting appropriate permissions with the ``X-Object-Sharing`` header. The permissions are applied using directory-based inheritance. A directory is an object with the corresponding content type. The default delimiter is ``/``. Thus, each set of authorization directives is applied to all objects in the directory object where the corresponding ``X-Object-Sharing`` header is defined. If there are nested/overlapping permissions, the closest to the object is applied. When retrieving an object, the ``X-Object-Shared-By`` header reports where it gets its permissions from. If not present, the object is the actual source of authorization directives.

A user may ``GET`` another account or container. The result will include a limited reply, containing only the allowed containers or objects respectively. A top-level request with an authentication token, will return a list of allowed accounts, so the user can easily find out which other users share objects. The ``X-Object-Allowed-To`` header lists the actions allowed on an object, if it does not belong to the requesting user.

Shared objects that are also public do not expose the ``X-Object-Public`` meta information.

Objects that are marked as public, via the ``X-Object-Public`` meta, are also available at the corresponding URI returned for ``HEAD`` or ``GET``. Requests for public objects do not need to include an ``X-Auth-Token``. Pithos will ignore request parameters and only include the following headers in the reply (all ``X-Object-*`` meta is hidden):

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
ETag                        The ETag of the object
Content-Length              The size of the data returned
Content-Type                The MIME content type of the object
Content-Range               The range of data included (only on a single range request)
Last-Modified               The last object modification date (regardless of version)
Content-Encoding            The encoding of the object (optional)
Content-Disposition         The presentation style of the object (optional)
==========================  ===============================

Public objects are not included and do not influence cross-user listings. They are, however, readable by all users.

Summary
^^^^^^^

List of differences from the OOS API:

* Support for ``X-Account-Meta-*`` style headers at the account level. Use ``POST`` to update.
* Support for ``X-Container-Meta-*`` style headers at the container level. Can be set when creating via ``PUT``. Use ``POST`` to update.
* Header ``X-Container-Object-Meta`` at the container level and parameter ``meta`` in container listings. (**TBD**)
* Account and container policies to manage behavior and limits. Container behavior overrides account settings. Account quota sets the maximum bytes limit, regardless of container values.
* Headers ``X-Container-Block-*`` at the container level, exposing the underlying storage characteristics.
* All metadata replies, at all levels, include latest modification information.
* At all levels, a ``HEAD`` or ``GET`` request may use ``If-Modified-Since`` and ``If-Unmodified-Since`` headers.
* Container/object lists include more fields if the reply is of type JSON/XML. Some names are kept to their OOS API equivalents for compatibility.
* Option to include only shared containers/objects in listings.
* Object metadata allowed, in addition to ``X-Object-Meta-*``: ``Content-Encoding``, ``Content-Disposition``, ``X-Object-Manifest``. These are all replaced with every update operation, except if using the ``update`` parameter (in which case individual keys can also be deleted). Deleting meta by providing empty values also works when copying/moving an object.
* Multi-range object ``GET`` support as outlined in RFC2616.
* Object hashmap retrieval through ``GET`` and the ``format`` parameter.
* Object create via hashmap through ``PUT`` and the ``format`` parameter.
* The object's Merkle hash is always returned in the ``X-Object-Hash`` header.
* The object's UUID is always returned in the ``X-Object-UUID`` header. The UUID remains unchanged, even when the object's data or metadata changes, or the object is moved to another path (is renamed). A new UUID is assigned when creating or copying an object.
* Object create using ``POST`` to support standard HTML forms.
* Partial object updates through ``POST``, using the ``Content-Length``, ``Content-Type``, ``Content-Range`` and ``Transfer-Encoding`` headers. Use another object's data to update with ``X-Source-Object`` and ``X-Source-Version``. Truncate with ``X-Object-Bytes``.
* Include new version identifier in replies for object replace/change requests.
* Object ``MOVE`` support and ``ignore_content_type`` parameter in both ``COPY`` and ``MOVE``.
* Conditional object create/update operations, using ``If-Match`` and ``If-None-Match`` headers.
* Time-variant account/container listings via the ``until`` parameter.
* Object versions - parameter ``version`` in ``HEAD``/``GET`` (list versions with ``GET``), ``X-Object-Version-*`` meta in replies, ``X-Source-Version`` in ``PUT``/``COPY``.
* Sharing/publishing with ``X-Object-Sharing``, ``X-Object-Public`` at the object level. Cross-user operations are allowed - controlled by sharing directives. Available actions in cross-user requests are reported with ``X-Object-Allowed-To``. Permissions may include groups defined with ``X-Account-Group-*`` at the account level. These apply to the object - not its versions.
* Support for directory-based inheritance when enforcing permissions. Parent object carrying the authorization directives is reported in ``X-Object-Shared-By``.
* Copy and move between accounts with ``X-Source-Account`` and ``Destination-Account`` headers.
* Large object support with ``X-Object-Manifest``.
* Trace the user that created/modified an object with ``X-Object-Modified-By``.
* Purge container/object history with the ``until`` parameter in ``DELETE``.
* Bulk COPY/MOVE/DELETE objects starting with prefix

Clarifications/suggestions:

* All non-ASCII characters in headers should be URL-encoded.
* Authentication is done by another system. The token is used in the same way, but it is obtained differently. The top level ``GET`` request is kept compatible with the OOS API and allows for guest/testing operations.
* Some processing is done in the variable part of all ``X-*-Meta-*`` headers. If it includes underscores, they will be converted to dashes and the first letter of all intra-dash strings will be capitalized.
* A ``GET`` reply for a level will include all headers of the corresponding ``HEAD`` request.
* To avoid conflicts between objects and virtual directory markers in container listings, it is recommended that object names do not end with the delimiter used.
* The ``Accept`` header may be used in requests instead of the ``format`` parameter to specify the desired request/reply format. The parameter overrides the header.
* Container/object lists use a ``200`` return code if the reply is of type JSON/XML. The reply will include an empty JSON/XML.
* In headers, dates are formatted according to RFC 1123. In extended information listings, the ``last_modified`` field is formatted according to ISO 8601 (for OOS API compatibility). All other fields (Pithos extensions) use integer tiemstamps.
* The ``Last-Modified`` header value always reflects the actual latest change timestamp, regardless of time control parameters and version requests. Time precondition checks with ``If-Modified-Since`` and ``If-Unmodified-Since`` headers are applied to this value.
* A copy/move using ``PUT``/``COPY``/``MOVE`` will always update metadata, keeping all old values except the ones redefined in the request headers.
* A ``HEAD`` or ``GET`` for an ``X-Object-Manifest`` object, will include modified ``Content-Length`` and ``ETag`` headers, according to the characteristics of the objects under the specified prefix. The ``Etag`` will be the MD5 hash of the corresponding ETags concatenated. In extended container listings there is no metadata processing.

Recommended Practices and Examples
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Assuming an authentication token is obtained, the following high-level operations are available - shown with ``curl``:

* Get account information ::

    curl -X HEAD -D - \
         -H "X-Auth-Token: 0000" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid

* List available containers ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid

* Get container information ::

    curl -X HEAD -D - \
         -H "X-Auth-Token: 0000" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/pithos

* Add a new container ::

    curl -X PUT -D - \
         -H "X-Auth-Token: 0000" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/test

* Delete a container ::

    curl -X DELETE -D - \
         -H "X-Auth-Token: 0000" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/test

* List objects in a container ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/pithos

* List objects in a container (extended reply) ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/pithos?format=json

  It is recommended that extended replies are cached and subsequent requests utilize the ``If-Modified-Since`` header.

* List metadata keys used by objects in a container

  Will be in the ``X-Container-Object-Meta`` reply header, included in container information or object list (``HEAD`` or ``GET``). (**TBD**)

* List objects in a container having a specific meta defined ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/pithos?meta=favorites

* Retrieve an object ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/pithos/README.txt

* Retrieve an object (specific ranges of data) ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         -H "Range: bytes=0-9" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/pithos/README.txt

  This will return the first 10 bytes. To get the first 10, bytes 30-39 and the last 100 use ``Range: bytes=0-9,30-39,-100``.

* Add a new object (folder type) (**TBD**) ::

    curl -X PUT -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Type: application/directory" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/pithos/folder

* Add a new object ::

    curl -X PUT -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Type: text/plain" \
         -T EXAMPLE.txt
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/pithos/folder/EXAMPLE.txt

* Update an object ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Length: 10" \
         -H "Content-Type: application/octet-stream" \
         -H "Content-Range: bytes 10-19/*" \
         -d "0123456789" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/folder/EXAMPLE.txt

  This will update bytes 10-19 with the data specified.

* Update an object (append) ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Length: 10" \
         -H "Content-Type: application/octet-stream" \
         -H "Content-Range: bytes */*" \
         -d "0123456789" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/folder/EXAMPLE.txt

* Update an object (truncate) ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "X-Source-Object: /folder/EXAMPLE.txt" \
         -H "Content-Range: bytes 0-0/*" \
         -H "X-Object-Bytes: 0" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/folder/EXAMPLE.txt

  This will truncate the object to 0 bytes.

* Add object metadata ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "X-Object-Meta-First: first_meta_value" \
         -H "X-Object-Meta-Second: second_meta_value" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/folder/EXAMPLE.txt

* Delete object metadata ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "X-Object-Meta-First: first_meta_value" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/folder/EXAMPLE.txt

  Metadata can only be "set". To delete ``X-Object-Meta-Second``, reset all metadata.

* Delete an object ::

    curl -X DELETE -D - \
         -H "X-Auth-Token: 0000" \
         https://storage.example.synnefo.org/pithos/object-store/v1.0/user-uuid/folder/EXAMPLE.txt
