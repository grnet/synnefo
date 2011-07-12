Pithos v2 Developer Guide
=========================

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

Document Revisions
^^^^^^^^^^^^^^^^^^

=========================  ================================
Revision                   Description
=========================  ================================
0.5 (July 12, 2011)        Object update from another object's data.
\                          Support object truncate.
0.4 (July 01, 2011)        Object permissions and account groups.
\                          Control versioning behavior and container quotas with container policy directives.
\                          Support updating/deleting individual metadata with ``POST``.
\                          Create object using hashmap.
0.3 (June 14, 2011)        Large object support with ``X-Object-Manifest``.
\                          Allow for publicly available objects via ``https://hostname/public``.
\                          Support time-variant account/container listings. 
\                          Add source version when duplicating with PUT/COPY.
\                          Request version in object HEAD/GET requests (list versions with GET).
0.2 (May 31, 2011)         Add object meta listing and filtering in containers.
\                          Include underlying storage characteristics in container meta.
\                          Support for partial object updates through POST.
\                          Expose object hashmaps through GET.
\                          Support for multi-range object GET requests.
0.1 (May 17, 2011)         Initial release. Based on OpenStack Object Storage Developer Guide API v1 (Apr. 15, 2011).
=========================  ================================

The Pithos API
--------------

The URI requests supported by the Pithos API follow one of the following forms:

* Top level: ``https://hostname/v1/``
* Account level: ``https://hostname/v1/<account>``
* Container level: ``https://hostname/v1/<account>/<container>``
* Object level: ``https://hostname/v1/<account>/<container>/<object>``

All requests must include an ``X-Auth-Token``. The process of obtaining the token is still to be determined (**TBD**).

The allowable request operations and respective return codes per level are presented in the remainder of this chapter. Common to all requests are the following return codes.

=========================  ================================
Return Code                Description
=========================  ================================
400 (Bad Request)          The request is invalid
401 (Unauthorized)         Request not allowed
404 (Not Found)            The requested resource was not found
503 (Service Unavailable)  The request cannot be completed because of an internal error
=========================  ================================

Top Level
^^^^^^^^^

List of operations:

=========  ==================
Operation  Description
=========  ==================
GET        Authentication. This is kept for compatibility with the OOS API
=========  ==================

GET
"""

If the ``X-Auth-User`` and ``X-Auth-Key`` headers are given, a dummy ``X-Auth-Token`` and ``X-Storage-Url`` will be replied, which can be used as a guest token/namespace for testing Pithos.

================  =====================
Return Code       Description
================  =====================
204 (No Content)  The request succeeded
================  =====================


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

======================  ===================================
Request Parameter Name  Value
======================  ===================================
until                   Optional timestamp
======================  ===================================

|

==========================  =====================
Reply Header Name           Value
==========================  =====================
X-Account-Container-Count   The total number of containers
X-Account-Object-Count      The total number of objects (**TBD**)
X-Account-Bytes-Used        The total number of bytes stored
X-Account-Bytes-Remaining   The total number of bytes remaining (**TBD**)
X-Account-Last-Login        The last login (**TBD**)
X-Account-Until-Timestamp   The last account modification date until the timestamp provided
X-Account-Group-*           Optional user defined groups
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
until                   Optional timestamp
======================  =========================

The reply is a list of container names. Account headers (as in a ``HEAD`` request) will also be included.
If a ``format=xml`` or ``format=json`` argument is given, extended information on the containers will be returned, serialized in the chosen format.
For each container, the information will include all container metadata (names will be in lower case and with hyphens replaced with underscores):

===========================  ============================
Name                         Description
===========================  ============================
name                         The name of the container
count                        The number of objects inside the container
bytes                        The total size of the objects inside the container
last_modified                The last container modification date (regardless of ``until``)
x_container_until_timestamp  The last container modification date until the timestamp provided
x_container_policy_*         Container behavior and limits
x_container_meta_*           Optional user defined metadata
===========================  ============================

For examples of container details returned in JSON/XML formats refer to the OOS API documentation.

===========================  =====================
Return Code                  Description
===========================  =====================
200 (OK)                     The request succeeded
204 (No Content)             The account has no containers (only for non-extended replies)
304 (Not Modified)           The account has not been modified
412 (Precondition Failed)    The condition set can not be satisfied
===========================  =====================

Will use a ``200`` return code if the reply is of type json/xml.


POST
""""

======================  ============================================
Request Parameter Name  Value
======================  ============================================
update                  Do not replace metadata/groups (no value parameter)
======================  ============================================

|

====================  ===========================
Request Header Name   Value
====================  ===========================
X-Account-Group-*     Optional user defined groups
X-Account-Meta-*      Optional user defined metadata
====================  ===========================

No reply content/headers.

The operation will overwrite all user defined metadata, except if ``update`` is defined.
To create a group, include an ``X-Account-Group-*`` header with the name in the key and a comma separated list of user names in the value. If no ``X-Account-Group-*`` header is present, no changes will be applied to groups. The ``update`` parameter also applies to groups. To delete a specific group, use ``update`` and an empty header value.

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

======================  ===================================
Request Parameter Name  Value
======================  ===================================
until                   Optional timestamp
======================  ===================================

|

===========================  ===============================
Reply Header Name            Value
===========================  ===============================
X-Container-Object-Count     The total number of objects in the container
X-Container-Bytes-Used       The total number of bytes of all objects stored
X-Container-Block-Size       The block size used by the storage backend
X-Container-Block-Hash       The hash algorithm used for block identifiers in object hashmaps
X-Container-Until-Timestamp  The last container modification date until the timestamp provided
X-Container-Object-Meta      A list with all meta keys used by objects
X-Container-Policy-*         Container behavior and limits
X-Container-Meta-*           Optional user defined metadata
Last-Modified                The last container modification date (regardless of ``until``)
===========================  ===============================

The keys returned in ``X-Container-Object-Meta`` are all the unique strings after the ``X-Object-Meta-`` prefix. See container ``PUT`` for a reference of policy directives.

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
meta                    Return objects having the specified meta keys (can be a comma separated list)
until                   Optional timestamp
======================  ===================================

The ``path`` parameter overrides ``prefix`` and ``delimiter``. When using ``path``, results will include objects ending in ``delimiter``.

The keys given with ``meta`` will be matched with the strings after the ``X-Object-Meta-`` prefix.

The reply is a list of object names. Container headers (as in a ``HEAD`` request) will also be included.
If a ``format=xml`` or ``format=json`` argument is given, extended information on the objects will be returned, serialized in the chosen format.
For each object, the information will include all object metadata (names will be in lower case and with hyphens replaced with underscores):

==========================  ======================================
Name                        Description
==========================  ======================================
name                        The name of the object
hash                        The ETag of the object
bytes                       The size of the object
content_type                The MIME content type of the object
content_encoding            The encoding of the object (optional)
content-disposition         The presentation style of the object (optional)
last_modified               The last object modification date (regardless of version)
x_object_version            The object's version identifier
x_object_version_timestamp  The object's version timestamp
x_object_modified_by        The user that committed the object's version
x_object_manifest           Object parts prefix in ``<container>/<object>`` form (optional)
x_object_sharing            Object permissions (optional)
x_object_shared_by          Object inheriting permissions (optional)
x_object_public             Object's publicly accessible URI (optional)
x_object_meta_*             Optional user defined metadata
==========================  ======================================

Extended replies may also include virtual directory markers in separate sections of the ``json`` or ``xml`` results.
Virtual directory markers are only included when ``delimiter`` is explicitly set. They correspond to the substrings up to and including the first occurrence of the delimiter.
In JSON results they appear as dictionaries with only a ``"subdir"`` key. In XML results they appear interleaved with ``<object>`` tags as ``<subdir name="..." />``.
In case there is an object with the same name as a virtual directory marker, the object will be returned.

For examples of object details returned in JSON/XML formats refer to the OOS API documentation.

===========================  ===============================
Return Code                  Description
===========================  ===============================
200 (OK)                     The request succeeded
204 (No Content)             The account has no containers (only for non-extended replies)
304 (Not Modified)           The container has not been modified
412 (Precondition Failed)    The condition set can not be satisfied
===========================  ===============================

Will use a ``200`` return code if the reply is of type json/xml.


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

* ``versioning``: Set to ``auto``, ``manual`` or ``none`` (default is ``manual``)
* ``quota``: Size limit in KB (default is ``0`` - unlimited)
 
================  ===============================
Return Code       Description
================  ===============================
201 (Created)     The container has been created
202 (Accepted)    The request has been accepted
================  ===============================


POST
""""

======================  ============================================
Request Parameter Name  Value
======================  ============================================
update                  Do not replace metadata/policy (no value parameter)
======================  ============================================

|

====================  ================================
Request Header Name   Value
====================  ================================
X-Container-Policy-*  Container behavior and limits
X-Container-Meta-*    Optional user defined metadata
====================  ================================

No reply content/headers.

The operation will overwrite all user defined metadata, except if ``update`` is defined.
To change policy, include an ``X-Container-Policy-*`` header with the name in the key. If no ``X-Container-Policy-*`` header is present, no changes will be applied to policy. The ``update`` parameter also applies to policy - deleted values will revert to defaults. To delete/revert a specific policy directive, use ``update`` and an empty header value. See container ``PUT`` for a reference of policy directives.

================  ===============================
Return Code       Description
================  ===============================
202 (Accepted)    The request has been accepted
================  ===============================


DELETE
""""""

No request parameters/headers.

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
X-Object-Version            The object's version identifier
X-Object-Version-Timestamp  The object's version timestamp
X-Object-Modified-By        The user that comitted the object's version
X-Object-Manifest           Object parts prefix in ``<container>/<object>`` form (optional)
X-Object-Sharing            Object permissions (optional)
X-Object-Shared-By          Object inheriting permissions (optional)
X-Object-Public             Object's publicly accessible URI (optional)
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
version                 Optional version identifier or ``list`` (specify a format if requesting a list)
======================  ===================================

The reply is the object's data (or part of it), except if a hashmap is requested with the ``format`` parameter, or a version list with ``version=list`` (in which case an extended reply format must be specified). Object headers (as in a ``HEAD`` request) are always included.

Hashmaps expose the underlying storage format of the object. Note that each hash is computed after trimming trailing null bytes of the corresponding block.

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

  {"versions": [[23, 1307700892], [28, 1307700898], ...]}

Example ``format=xml`` reply:

::

  <?xml version="1.0" encoding="UTF-8"?>
  <object name="file">
    <version timestamp="1307700892">23</version>
    <version timestamp="1307700898">28</version>
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
X-Object-Version            The object's version identifier
X-Object-Version-Timestamp  The object's version timestamp
X-Object-Modified-By        The user that comitted the object's version
X-Object-Manifest           Object parts prefix in ``<container>/<object>`` form (optional)
X-Object-Sharing            Object permissions (optional)
X-Object-Shared-By          Object inheriting permissions (optional)
X-Object-Public             Object's publicly accessible URI (optional)
X-Object-Meta-*             Optional user defined metadata
==========================  ===============================

|

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
ETag                  The MD5 hash of the object (optional to check written data)
Content-Length        The size of the data written
Content-Type          The MIME content type of the object
Transfer-Encoding     Set to ``chunked`` to specify incremental uploading (if used, ``Content-Length`` is ignored)
X-Copy-From           The source path in the form ``/<container>/<object>``
X-Move-From           The source path in the form ``/<container>/<object>``
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
format                  Optional extended request type (can be ``json``) to create the object by suppling its hashmap instead
======================  ===================================

The request is the object's data (or part of it), except if a hashmap is provided with the ``format`` parameter.  If format is used and all different parts are stored in the server, the object is created otherwise the server returns Conflict (409) with the list of the missing parts. 

Hashmaps expose the underlying storage format of the object.

Example ``format=json`` request:

::

  {"block_hash": "sha1", "hashes": ["7295c41da03d7f916440b98e32c4a2a39351546c", ...], "block_size": 131072, "bytes": 242}


==========================  ===============================
Reply Header Name           Value
==========================  ===============================
ETag                        The MD5 hash of the object (on create)
==========================  ===============================

The ``X-Object-Sharing`` header may include either a ``read=...`` comma-separated user/group list, or a ``write=...`` comma-separated user/group list, or both separated by a semicolon (``;``). To publish the object, set ``X-Object-Public`` to ``true``. To unpublish, set to ``false``, or use an empty header value.

===========================  ==============================
Return Code                  Description
===========================  ==============================
201 (Created)                The object has been created
409 (Conflict)               The object can not be created from the provided hashmap, or there are conflicting permissions (a list of missing hashes, or a conflicting sharing path will be included in the reply - in JSON format)
411 (Length Required)        Missing ``Content-Length`` or ``Content-Type`` in the request
422 (Unprocessable Entity)   The MD5 checksum of the data written to the storage system does not match the (optionally) supplied ETag value
===========================  ==============================


COPY
""""

====================  ================================
Request Header Name   Value
====================  ================================
Destination           The destination path in the form ``/<container>/<object>``
Content-Type          The MIME content type of the object (optional)
Content-Encoding      The encoding of the object (optional)
Content-Disposition   The presentation style of the object (optional)
X-Source-Version      The source version to copy from
X-Object-Manifest     Object parts prefix in ``<container>/<object>`` form (optional)
X-Object-Sharing      Object permissions (optional)
X-Object-Public       Object is publicly accessible (optional)
X-Object-Meta-*       Optional user defined metadata
====================  ================================

Refer to ``PUT``/``POST`` for a description of request headers. Metadata is also copied, updated with any values defined. Sharing/publishing options are not copied.

No reply content/headers.

===========================  ==============================
Return Code                  Description
===========================  ==============================
201 (Created)                The object has been created
409 (Conflict)               There are conflicting permissions (a conflicting sharing path will be included in the reply - in JSON format)
===========================  ==============================


MOVE
""""

Same as ``COPY``, without the ``X-Source-Version`` request header. The ``MOVE`` operation is always applied on the latest version.


POST
""""

======================  ============================================
Request Parameter Name  Value
======================  ============================================
update                  Do not replace metadata (no value parameter)
======================  ============================================

|

====================  ================================
Request Header Name   Value
====================  ================================
Content-Length        The size of the data written (optional, to update)
Content-Type          The MIME content type of the object (optional, to update)
Content-Range         The range of data supplied (optional, to update)
Transfer-Encoding     Set to ``chunked`` to specify incremental uploading (if used, ``Content-Length`` is ignored)
Content-Encoding      The encoding of the object (optional)
Content-Disposition   The presentation style of the object (optional)
X-Source-Object       Update with data from the object at path ``/<container>/<object>`` (optional, to update)
X-Source-Version      The source version to update from (optional, to update)
X-Object-Bytes        The updated object's final size (optional, when updating)
X-Object-Manifest     Object parts prefix in ``<container>/<object>`` form (optional)
X-Object-Sharing      Object permissions (optional)
X-Object-Public       Object is publicly accessible (optional)
X-Object-Meta-*       Optional user defined metadata
====================  ================================

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

A data update will trigger an ETag change. The new ETag will not correspond to the object's MD5 sum (**TBD**) and will be included in reply headers.

No reply content. No reply headers if only metadata is updated.

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
ETag                        The new ETag of the object (data updated)
==========================  ===============================

|

===========================  ==============================
Return Code                  Description
===========================  ==============================
202 (Accepted)               The request has been accepted (not a data update)
204 (No Content)             The request succeeded (data updated)
409 (Conflict)               There are conflicting permissions (a conflicting sharing path will be included in the reply - in JSON format)
411 (Length Required)        Missing ``Content-Length`` in the request
416 (Range Not Satisfiable)  The supplied range is invalid
===========================  ==============================


DELETE
""""""

No request parameters/headers.

No reply content/headers.

===========================  ==============================
Return Code                  Description
===========================  ==============================
204 (No Content)             The request succeeded
===========================  ==============================

Sharing and Public Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^

Read and write control in Pithos is managed by setting appropriate permissions with the ``X-Object-Sharing`` header. The permissions are applied using prefix-based inheritance. Thus, each set of authorization directives is applied to all objects sharing the same prefix with the object where the corresponding ``X-Object-Sharing`` header is defined. For simplicity, nested/overlapping permissions are not allowed. Setting ``X-Object-Sharing`` will fail, if the object is already "covered", or another object with a longer common-prefix name already has permissions. When retrieving an object, the ``X-Object-Shared-By`` header reports where it gets its permissions from. If not present, the object is the actual source of authorization directives.

Objects that are marked as public, via the ``X-Object-Public`` meta, are also available at the corresponding URI returned for ``HEAD`` or ``GET``. Requests for public objects do not need to include an ``X-Auth-Token``. Pithos will ignore request parameters and only include the following headers in the reply (all ``X-Object-*`` meta is hidden).

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

Summary
^^^^^^^

List of differences from the OOS API:

* Support for ``X-Account-Meta-*`` style headers at the account level. Use ``POST`` to update.
* Support for ``X-Container-Meta-*`` style headers at the container level. Can be set when creating via ``PUT``. Use ``POST`` to update.
* Header ``X-Container-Object-Meta`` at the container level and parameter ``meta`` in container listings.
* Container policies to manage behavior and limits.
* Headers ``X-Container-Block-*`` at the container level, exposing the underlying storage characteristics.
* All metadata replies, at all levels, include latest modification information.
* At all levels, a ``GET`` request may use ``If-Modified-Since`` and ``If-Unmodified-Since`` headers.
* Container/object lists include all associated metadata if the reply is of type json/xml. Some names are kept to their OOS API equivalents for compatibility. 
* Object metadata allowed, in addition to ``X-Object-Meta-*``: ``Content-Encoding``, ``Content-Disposition``, ``X-Object-Manifest``. These are all replaced with every update operation, except if using the ``update`` parameter (in which case individual keys can also be deleted). Deleting meta by providing empty values also works when copying/moving an object.
* Multi-range object GET support as outlined in RFC2616.
* Object hashmap retrieval through GET and the ``format`` parameter.
* Partial object updates through POST, using the ``Content-Length``, ``Content-Type``, ``Content-Range`` and ``Transfer-Encoding`` headers. Use another object's data to update with ``X-Source-Object`` and ``X-Source-Version``. Truncate with ``X-Object-Bytes``.
* Object ``MOVE`` support.
* Time-variant account/container listings via the ``until`` parameter.
* Object versions - parameter ``version`` in HEAD/GET (list versions with GET), ``X-Object-Version-*`` meta in replies, ``X-Source-Version`` in PUT/COPY.
* Sharing/publishing with ``X-Object-Sharing``, ``X-Object-Public`` at the object level. Permissions may include groups defined with ``X-Account-Group-*`` at the account level. These apply to the object - not its versions.
* Support for prefix-based inheritance when enforcing permissions. Parent object carrying the authorization directives is reported in ``X-Object-Shared-By``.
* Large object support with ``X-Object-Manifest``.
* Trace the user that created/modified an object with ``X-Object-Modified-By``.

Clarifications/suggestions:

* Authentication is done by another system. The token is used in the same way, but it is obtained differently. The top level ``GET`` request is kept compatible with the OOS API and allows for guest/testing operations.
* Some processing is done in the variable part of all ``X-*-Meta-*`` headers. If it includes underscores, they will be converted to dashes and the first letter of all intra-dash strings will be capitalized.
* A ``GET`` reply for a level will include all headers of the corresponding ``HEAD`` request.
* To avoid conflicts between objects and virtual directory markers in container listings, it is recommended that object names do not end with the delimiter used.
* The ``Accept`` header may be used in requests instead of the ``format`` parameter to specify the desired reply format. The parameter overrides the header.
* Container/object lists use a ``200`` return code if the reply is of type json/xml. The reply will include an empty json/xml.
* In headers, dates are formatted according to RFC 1123. In extended information listings, dates are formatted according to ISO 8601.
* The ``Last-Modified`` header value always reflects the actual latest change timestamp, regardless of time control parameters and version requests. Time precondition checks with ``If-Modified-Since`` and ``If-Unmodified-Since`` headers are applied to this value.
* A copy/move using ``PUT``/``COPY``/``MOVE`` will always update metadata, keeping all old values except the ones redefined in the request headers.
* A ``HEAD`` or ``GET`` for an ``X-Object-Manifest`` object, will include modified ``Content-Length`` and ``ETag`` headers, according to the characteristics of the objects under the specified prefix. The ``Etag`` will be the MD5 hash of the corresponding ETags concatenated. In extended container listings there is no metadata processing.

The Pithos Client
-----------------

User Experience
^^^^^^^^^^^^^^^

Hopefully this API will allow for a multitude of client implementations, each supporting a different device or operating system. All clients will be able to manipulate containers and objects - even software only designed for OOS API compatibility. But a Pithos interface should not be only about showing containers and folders. There are some extra user interface elements and functionalities that should be common to all implementations.

Upon entrance to the service, a user is presented with the following elements - which can be represented as folders or with other related icons:

* The ``home`` element, which is used as the default entry point to the user's "files". Objects under ``home`` are represented in the usual hierarchical organization of folders and files.
* The ``trash`` element, which contains files that have been marked for deletion, but can still be recovered.
* The ``shared`` element, which contains all objects shared by the user to other users of the system.
* The ``others`` element, which contains all objects that other users share with the user.
* The ``tags`` element, which lists the names of tags the user has defined. This can be an entry point to list all files that have been assigned a specific tag or manage tags in general (remove a tag completely, rename a tag etc.).
* The ``groups`` element, which contains the names of groups the user has defined. Each group consists of a user list. Group creation, deletion, and manipulation is carried out by actions originating here.

Objects in Pithos can be:

* Assigned custom tags.
* Moved to trash and then deleted.
* Shared with specific permissions.
* Made public (shared with non-Pithos users).
* Restored from previous versions.

Some of these functions are performed by the client software and some by the Pithos server. Client-driven functionality is based on specific metadata that should be handled equally across implementations. These metadata names are discussed in the next chapter. 

Conventions and Metadata Specification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pithos clients should use the ``pithos`` container for all Pithos objects. Object names use the ``/`` delimiter to impose a hierarchy of folders and files.

At the object level, tags are implemented by managing metadata keys. The client software should allow the user to use any string as a tag and then set the corresponding ``X-Object-Meta-<tag>`` key at the server. The API extensions provided, allow for listing all tags in a container and filtering object listings based on one or more tags. The tag list is sufficient for implementing the ``tags`` element, either as a special, virtual folder (as done in the first version of Pithos), or as an application menu.

The metadata specification is summarized in the following table.

===========================  ==============================
Metadata Name                Value
===========================  ==============================
X-Object-Meta-*              Use for other tags that apply to the object
===========================  ==============================

Recommended Practices and Examples
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Assuming an authentication token is obtained (**TBD**), the following high-level operations are available - shown with ``curl``:

* Get account information ::

    curl -X HEAD -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user

* List available containers ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user

* Get container information ::

    curl -X HEAD -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/pithos

* Add a new container ::

    curl -X PUT -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/test

* Delete a container ::

    curl -X DELETE -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/test

* List objects in a container ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/pithos

* List objects in a container (extended reply) ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/pithos?format=json

  It is recommended that extended replies are cached and subsequent requests utilize the ``If-Modified-Since`` header.

* List metadata keys used by objects in a container

  Will be in the ``X-Container-Object-Meta`` reply header, included in container information or object list (``HEAD`` or ``GET``).

* List objects in a container having a specific meta defined ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/pithos?meta=favorites

* Retrieve an object ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/pithos/README.txt

* Retrieve an object (specific ranges of data) ::

    curl -X GET -D - \
         -H "X-Auth-Token: 0000" \
         -H "Range: bytes=0-9" \
         https://pithos.dev.grnet.gr/v1/user/pithos/README.txt

  This will return the first 10 bytes. To get the first 10, bytes 30-39 and the last 100 use ``Range: bytes=0-9,30-39,-100``.

* Add a new object (folder type) (**TBD**) ::

    curl -X PUT -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Type: application/folder" \
         https://pithos.dev.grnet.gr/v1/user/pithos/folder

* Add a new object ::

    curl -X PUT -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Type: text/plain" \
         -T EXAMPLE.txt
         https://pithos.dev.grnet.gr/v1/user/pithos/folder/EXAMPLE.txt

* Update an object ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Length: 10" \
         -H "Content-Type: application/octet-stream" \
         -H "Content-Range: bytes 10-19/*" \
         -d "0123456789" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt

  This will update bytes 10-19 with the data specified.

* Update an object (append) ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "Content-Length: 10" \
         -H "Content-Type: application/octet-stream" \
         -H "Content-Range: bytes */*" \
         -d "0123456789" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt

* Update an object (truncate) ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "X-Source-Object: /folder/EXAMPLE.txt" \
         -H "Content-Range: bytes 0-0/*" \
         -H "X-Object-Bytes: 0" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt

  This will truncate the object to 0 bytes.

* Add object metadata ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "X-Object-Meta-First: first_meta_value" \
         -H "X-Object-Meta-Second: second_meta_value" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt

* Delete object metadata ::

    curl -X POST -D - \
         -H "X-Auth-Token: 0000" \
         -H "X-Object-Meta-First: first_meta_value" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt

  Metadata can only be "set". To delete ``X-Object-Meta-Second``, reset all metadata.

* Delete an object ::

    curl -X DELETE -D - \
         -H "X-Auth-Token: 0000" \
         https://pithos.dev.grnet.gr/v1/user/folder/EXAMPLE.txt
