Pithos v2 Developer Guide
=========================

Introduction
------------

Pithos is a storage service implemented by GRNET (http://www.grnet.gr). Data is stored as objects, organized in containers, belonging to an account. This hierarchy of storage layers has been inspired by the OpenStack Object Storage (OOS) API and similar CloudFiles API by Rackspace. The Pithos API follows the OOS API as closely as possible. One of the design requirements has been to be able to use Pithos with clients built for the OOS, without changes.

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
0.2 (May 25, 2011)         Add object meta listing and filtering in containers.
\                          Support for multi-range object GET requests.
0.1 (May 17, 2011)         Initial release. Based on OpenStack Object Storage Developer Guide API v1 (Apr. 15, 2011).
=========================  ================================

The Pithos API
--------------

The URI requests supported by Pithos follow one of the following forms:

* Top level: ``https://hostname/v1/``
* Account level: ``https://hostname/v1/<account>``
* Container level: ``https://hostname/v1/<account>/<container>``
* Object level: ``https://hostname/v1/<account>/<container>/<object>``

All requests must include an ``X-Auth-Token``, except from those that refer to publicly available files (**TBD**). The process of obtaining the token is still to be determined (**TBD**).

The allowable request operations and corresponding return codes per level are presented in the remainder of this chapter. Common to all requests are the following return codes.

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

No request parameters/headers.

==========================  =====================
Reply Header Name           Value
==========================  =====================
X-Account-Container-Count   The total number of containers
X-Account-Object-Count      The total number of objects (**TBD**)
X-Account-Bytes-Used        The total number of bytes stored
X-Account-Bytes-Remaining   The total number of bytes remaining (**TBD**)
X-Account-Last-Login        The last login (**TBD**)
X-Account-Meta-*            Optional user defined metadata
Last-Modified               The last object modification date
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
======================  =========================

The reply is a list of container names. Account headers (as in a ``HEAD`` request) will also be included.
If a ``format=xml`` or ``format=json`` argument is given, extended information on the containers will be returned, serialized in the chosen format.
For each container, the information will include all container metadata (names will be in lower case and with hyphens replaced with underscores):

===================  ============================
Name                 Description
===================  ============================
name                 The name of the container
count                The number of objects inside the container
bytes                The total size of the objects inside the container
last_modified        The last object modification date
x_container_meta_*   Optional user defined metadata
===================  ============================

For examples of container details returned in JSON/XML formats refer to the OOS API documentation.

================  =====================
Return Code       Description
================  =====================
200 (OK)          The request succeeded
204 (No Content)  The account has no containers (only for non-extended replies)
================  =====================

Will use a ``200`` return code if the reply is of type json/xml.


POST
""""

====================  ===========================
Request Header Name   Value
====================  ===========================
X-Account-Meta-*      Optional user defined metadata
====================  ===========================

No reply content/headers.

The update operation will overwrite all user defined metadata.

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

No request parameters/headers.

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
X-Container-Object-Count    The total number of objects in the container
X-Container-Bytes-Used      The total number of bytes of all objects stored
X-Container-Meta-*          Optional user defined metadata
X-Container-Object-Meta     A list with all meta keys used by objects
Last-Modified               The last object modification date
==========================  ===============================

The keys returned in ``X-Container-Object-Meta`` are all the unique strings after the ``X-Object-Meta-`` prefix.

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
======================  ===================================

The ``path`` parameter overrides ``prefix`` and ``delimiter``. When using ``path``, results will include objects ending in ``delimiter``.

The keys given with ``meta`` will be matched with the strings after the ``X-Object-Meta-`` prefix.

The reply is a list of object names. Container headers (as in a ``HEAD`` request) will also be included.
If a ``format=xml`` or ``format=json`` argument is given, extended information on the objects will be returned, serialized in the chosen format.
For each object, the information will include all object metadata (names will be in lower case and with hyphens replaced with underscores):

===================  ======================================
Name                 Description
===================  ======================================
name                 The name of the object
hash                 The MD5 hash of the object
bytes                The size of the object
content_type         The MIME content type of the object
content_encoding     The encoding of the object (optional)
last_modified        The last object modification date
x_object_manifest    Large object support
x_object_meta_*      Optional user defined metadata
===================  ======================================

Extended replies may also include virtual directory markers in separate sections of the ``json`` or ``xml`` results.
Virtual directory markers are only included when ``delimiter`` is explicitly set. They correspond to the substrings up to and including the first occurrence of the delimiter.
In JSON results they appear as dictionaries with only a ``"subdir"`` key. In XML results they appear interleaved with ``<object>`` tags as ``<subdir name="..." />``.
In case there is an object with the same name as a virtual directory marker, the object will be returned.
 
For examples of object details returned in JSON/XML formats refer to the OOS API documentation.

================  ===============================
Return Code       Description
================  ===============================
200 (OK)          The request succeeded
204 (No Content)  The account has no containers (only for non-extended replies)
================  ===============================

Will use a ``200`` return code if the reply is of type json/xml.


PUT
"""

====================  ================================
Request Header Name   Value
====================  ================================
X-Container-Meta-*    Optional user defined metadata
====================  ================================
 
No reply content/headers.
 
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
X-Container-Meta-*    Optional user defined metadata
====================  ================================

No reply content/headers.

The update operation will overwrite all user defined metadata.

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
POST       Update object metadata
DELETE     Delete object
=========  =================================


HEAD
""""

No request parameters/headers.

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
ETag                        The MD5 hash of the object
Content-Length              The size of the object
Content-Type                The MIME content type of the object
Last-Modified               The last object modification date
Content-Encoding            The encoding of the object (optional)
Content-Disposition         The presentation style of the object (optional)
X-Object-Manifest           Large object support (optional)
X-Object-Meta-*             Optional user defined metadata
==========================  ===============================

|

================  ===============================
Return Code       Description
================  ===============================
204 (No Content)  The request succeeded
================  ===============================


GET
"""

====================  ================================
Request Header Name   Value
====================  ================================
Range                 Optional range of data to retrieve
If-Match              Retrieve if ETags match
If-None-Match         Retrieve if ETags don't match
If-Modified-Since     Retrieve if object has changed since provided timestamp
If-Unmodified-Since   Retrieve if object has not changed since provided timestamp
====================  ================================

The reply is the object's data (or part of it). Object headers (as in a ``HEAD`` request) will also be included.

The ``Range`` header may include multiple ranges, as outlined in RFC2616. Then the ``Content-Type`` of the reply will be ``multipart/byteranges`` and each part will include a ``Content-Range`` header.

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
ETag                        The MD5 hash of the object
Content-Length              The size of the data returned
Content-Type                The MIME content type of the object
Content-Range               The range of data included (only on a single range request)
Last-Modified               The last object modification date
Content-Encoding            The encoding of the object (optional)
Content-Disposition         The presentation style of the object (optional)
X-Object-Manifest           Large object support (optional)
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
Content-Encoding      The encoding of the object (optional)
Content-Disposition   The presentation style of the object (optional)
X-Object-Manifest     Large object support (optional)
X-Object-Meta-*       Optional user defined metadata
====================  ================================

|

==========================  ===============================
Reply Header Name           Value
==========================  ===============================
ETag                        The MD5 hash of the object (on create)
==========================  ===============================

|

===========================  ==============================
Return Code                  Description
===========================  ==============================
201 (Created)                The object has been created
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
X-Object-Manifest     Large object support (optional)
X-Object-Meta-*       Optional user defined metadata
====================  ================================

No reply content/headers.

===========================  ==============================
Return Code                  Description
===========================  ==============================
201 (Created)                The object has been created
===========================  ==============================


MOVE
""""

Same as ``COPY``.


POST
""""

====================  ================================
Request Header Name   Value
====================  ================================
Content-Encoding      The encoding of the object (optional)
Content-Disposition   The presentation style of the object (optional)
X-Object-Manifest     Large object support (optional)
X-Object-Meta-*       Optional user defined metadata
====================  ================================

No reply content/headers.

The allowed headers are considered to be user defined metadata. The update operation will overwrite all previous values and remove any keys not supplied.

===========================  ==============================
Return Code                  Description
===========================  ==============================
202 (Accepted)               The request has been accepted
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


Summary
^^^^^^^

List of differences from the OOS API:

* Support for ``X-Account-Meta-*`` style headers at the account level. Use ``POST`` to update.
* Support for ``X-Container-Meta-*`` style headers at the account level. Can be set when creating via ``PUT``. Use ``POST`` to update.
* Header ``X-Container-Object-Meta`` at the container level and parameter ``meta`` in container listings.
* All metadata replies, at all levels, include latest modification information.
* At all levels, a ``GET`` request may use ``If-Modified-Since`` and ``If-Unmodified-Since`` headers.
* Container/object lists include all associated metadata if the reply is of type json/xml. Some names are kept to their OOS API equivalents for compatibility. 
* Object metadata allowed, in addition to ``X-Object-Meta-*``: ``Content-Encoding``, ``Content-Disposition``, ``X-Object-Manifest``. These are all replaced with every update operation.
* Multi-range object GET support as outlined in RFC2616.
* Object ``MOVE`` support.

Clarifications/suggestions:

* Authentication is done by another system. The token is used in the same way, but it is obtained differently. The top level ``GET`` request is kept compatible with the OOS API and allows for guest/testing operations.
* Some processing is done in the variable part of all ``X-*-Meta-*`` headers. If it includes underscores, they will be converted to dashes and the first letter of all intra-dash strings will be capitalized.
* A ``GET`` reply for a level will include all headers of the corresponding ``HEAD`` request.
* To avoid conflicts between objects and virtual directory markers in container listings, it is recommended that object names do not end with the delimiter used.
* The ``Accept`` header may be used in requests instead of the ``format`` parameter to specify the desired reply format. The parameter overrides the header.
* Container/object lists use a ``200`` return code if the reply is of type json/xml. The reply will include an empty json/xml.
* In headers, dates are formatted according to RFC 1123. In extended information listings, dates are formatted according to ISO 8601.
* While ``X-Object-Manifest`` can be set and unset, large object support is not yet implemented (**TBD**).

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
* Set to monitor changes via version tracking.

Some of these functions are performed by the client software and some by the Pithos server. Client-driven functionality is based on specific metadata that should be handled equally across implementations. These metadata names are discussed in the next chapter. 

Conventions and Metadata Specification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pithos clients should use the ``pithos`` container for all Pithos objects. Object names use the ``/`` delimiter to impose a hierarchy of folders and files.

At the object level, tags are implemented by managing metadata keys. The client software should allow the user to use any string as a tag (except ``trash``) and then set the corresponding ``X-Object-Meta-<tag>`` key at the server. The API extensions provided, allow for listing all tags in a container and filtering object listings based on one or more tags. The tag list is sufficient for implementing the ``tags`` element, either as a special, virtual folder (as done in the first version of Pithos), or as an application menu.

To manage the deletion of files use the same API and the ``X-Object-Meta-Trash`` key. The string ``trash`` can not be used as a tag. The ``trash`` element should be presented as a folder, although with no hierarchy.

The metadata specification is summarized in the following table.

===========================  ==============================
Metadata Name                Value
===========================  ==============================
X-Object-Meta-Trash          Set to ``true`` if the object has been moved to the trash
X-Object-Meta-*              Use for other tags that apply to the object
===========================  ==============================
