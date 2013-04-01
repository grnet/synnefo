.. _plankton-api-guide:

Plankton API Guide
==================

Introduction
------------

Plankton is an image service implemented by `GRNET <http://www.grnet.gr>`_ as part of the `Synnefo <http://www.synnefo.org>`_ cloud software, and implements an extension of the `OpenStack Image API <http://docs.openstack.org/api/openstack-image-service/1.1/content/>`_. To take full advantage of the Plankton infrastructure, client software should be aware of the extensions that differentiate Plankton from OOSs `Glance <http://docs.openstack.org/developer/glance/glanceapi.html>`_.

This document's goals are:

* Define the Plankton ReST API
* Clarify the differences between Plankton and Glance
* Specify metadata semantics and user interface guidelines for a common experience across client software implementations

Image ReST API
--------------
========================================= ===================================== ====== ======== ======
Description                               URI                                   Method Plankton Glance
========================================= ===================================== ====== ======== ======
`List Available Images <#id2>`_           ``/images``                           GET    ✔        ✔
`List Available Images in Detail <#id3>`_ ``/images/detail``                    GET    ✔        ✔
`Add or update an Image <#id6>`_          ``/images``                           POST   ✔        ✔
`Update an Image <#id9>`_                 ``/images``                           PUT    **✘**    ✔
\                                         ``/images/<img-id>``                  PUT    ✔        **✘**
`Retrieve Image Metadata <#id10>`_        ``/images/<img-id>``                  HEAD   ✔        ✔
`Retrieve Raw Image Data <#id12>`_        ``/images/<img-id>``                  GET    **✘**    ✔
`List Image Memberships <#id14>`_         ``/images/<img-id>/members``          GET    ✔        ✔
`Replace a Membership List <#id15>`_      ``/images/<img-id>/members``          PUT    ✔        ✔
`Add a Member to an Image <#id11>`_       ``/images/<img-id>/members/<member>`` PUT    ✔        ✔
`Remove a Member from an Image <#id12>`_  ``/images/<img-id>/members/<member>`` DELETE ✔        ✔
`List Shared Images <#id13>`_             ``/shared-images/<member>``           GET    ✔        ✔
========================================= ===================================== ====== ======== ======

Authentication
--------------

**Plankton** depends on Astakos to handle authentication of clients. An authentication token must be obtained from the identity manager which should be send along with each API requests through the *X-Auth-Token* header. Plankton handles the communication with Astakos to verify the token validity and obtain identity credentials.

**Glance** handles authentication in a `similar manner <http://docs.openstack.org/developer/glance/glanceapi.html#authentication>`_, with the only difference being the suggested identity manager.


List Available Images
---------------------

This request returns a list of all images accessible by the user. In specific, the list contains images falling at one of the following categories:

* registered by the user
* shared to  user by others
* public

=========== ====== ======== ======
URI         Method Plankton Glance
=========== ====== ======== ======
``/images`` GET    ✔        ✔
=========== ====== ======== ======

|

====================== ======================================= ======== ======
Request Parameter Name Value                                   Plankton Glance
====================== ======================================= ======== ======
name                   Return images of given name             ✔        ✔
container_format       Return images of given container format ✔        ✔
disk_format            Return images of given disk format      ✔        ✔
status                 Return images of given status           ✔        ✔
size_min               Return images of size >= to given value ✔        ✔
size_max               Return images of size >= to given value ✔        ✔
sort_key               Sort images against given key           ✔        ✔
sort_dir               Sort images in given direction          ✔        ✔
====================== ======================================= ======== ======

**container_format** values are listed at :ref:`container-format-ref`

**disk_format** values are listed at :ref:`disk-format-ref`

**sort_key** values: id, name, status, size, disk_format, container_format, created_at, updated_at

======== ================ ======== =======
sort_dir Description      Plankton Glance
======== ================ ======== =======
asc      Ascending order  default  default
desc     Descending order ✔        ✔
======== ================ ======== =======

|

====================  ========================= ======== =========
Request Header Name   Value                     Plankton Glance
====================  ========================= ======== =========
X-Auth-Token          User authentication token required  required
====================  ========================= ======== =========

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           Raised in case of invalid values for
\                           *sort_key*, *sort_dir*, *size_max* or *size_min*
401 (Unauthorized)          Missing or expired user token
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

The response data is a list of images in a json format containing the fields presented bellow

================ ===================== ======== ======
Name             Description           Plankton Glance
================ ===================== ======== ======
id               A unique image id      ✔        **✘**
uri              Unique id in URI form **✘**    ✔
name             The name of the image ✔        ✔
status           ???The VM status???   ✔        **✘**
disk_format      The disc format       ✔        ✔
container_format The container format  ✔        ✔
size             Image size in bytes   ✔        ✔
================ ===================== ======== ======

Example Plankton response:

::

    [{
        "status": "available", 
        "name": "ubuntu", 
        "disk_format": "diskdump", 
        "container_format": "bare", 
        "id": "5583ffe1-5273-4c84-9e32-2fbe476bd7b7", 
        "size": 2622562304
    }, {
        "status": "available", 
        "name": "Ubuntu-10.04", 
        "disk_format": "diskdump", 
        "container_format": "bare", 
        "id": "907ef618-c03a-4473-9914-9348e12890c1", 
        "size": 761368576
    }]

List Available Images in Detail
-------------------------------

This request returns the same list of images as in `List Available Images <#id2>`_, but the results are reacher in metadata.

================== ====== ======== ======
URI                Method Plankton Glance
================== ====== ======== ======
``/images/detail`` GET    ✔        ✔
================== ====== ======== ======

**Request parameters** and **headers** as well as **response headers** and **error codes** are exactly the same as in `List Available Images <#id2>`_, both syntactically and semantically.


The response data is a list of images in json format containing the fields presented bellow

================ ===================== ======== ======
Name             Description           Plankton Glance
================ ===================== ======== ======
id               A unique image id     ✔        **✘**
uri              Unique id in URI form **✘**    ✔
location         Pithos+ file location ✔        **✘**
name             The name of the image ✔        ✔
status           ???The VM status???   ✔        **✘**
disk_format      The disc format       ✔        ✔
container_format The container format  ✔        ✔
size             Image size in bytes   ✔        ✔
checksum         file MD5 checksum     ✔        ✔
created_at       Timestamp of creation ✔        ✔
updated_at       Timestamp of update   ✔        ✔
deleted_at       Timestamp of deletion ✔        ✔
is_public        True if img is public ✔        ✔
min_ram          Minimum ram required  **✘**    ✔
min_disk         Maximum ram required  **✘**    ✔
owner            Image owner           ✔        ✔
properties       Custom properties     ✔        ✔
================ ===================== ======== ======

|

Example Plankton response::

    [{
        "status": "available", 
        "location": "pithos://u53r-1d/images/my/path/example_image_build.diskdump"
        "name": "ubuntu", 
        "disk_format": "diskdump", 
        "container_format": "bare", 
        "created_at": "2013-03-29 14:14:34",
        "deleted_at": "",
        "id": "5583ffe1-5273-4c84-9e32-2fbe476bd7b7",
        "size": 2622562304,
        "is_public": "True",
        "checksum": "a387aaaae583bc65daacf12d6be502bd7cfbbb254dcd452f92ca31f4c06a9208",
        "properties": {
            "partition_table": "msdos", 
            "kernel": "3.8.3", 
            "osfamily": "linux", 
            "users": "root user", 
            "gui": "GNOME 3.4.2", 
            "sortorder": "5", 
            "os": "fedora", 
            "root_partition": "1", 
            "description": "Fedora release 17 (Beefy Miracle)"}
    }, {
        "location": "pithos://0th3r-u53r-1d/images/ubuntu_10_04.diskdump"
        "status": "available", 
        "name": "Ubuntu-10.04", 
        "disk_format": "diskdump", 
        "container_format": "bare", 
        "id": "907ef618-c03a-4473-9914-9348e12890c1", 
        "size": 761368576
        "created_at": "2013-03-29 14:14:34",
        "deleted_at": ""
    }]

Add or update an image
----------------------

According to the Synnefo approach, this request performs two functionalities:

* registers a new image to Plankton
* commits metadata for the new image
* update the metadata of an existing image

The physical image file must be uploaded on a `Pithos+ <pithos.html>`_ server, at a space accessible by the user. The Pithos+ location of the physical file acts as a key for the image (image ids and image locations are uniquely coupled).

According to the OpenStack approach, this request performs the first two functionalities by uploading the the image data and metadata to Glance. In Glance, the update mechanism is not implemented with this specific request.

=========== ====== ======== ======
URI         Method Plankton Glance
=========== ====== ======== ======
``/images`` POST   ✔        ✔
=========== ====== ======== ======

|

============================= ========================= ========  ========
Request Header Name           Value                     Plankton  Glance
============================= ========================= ========  ========
X-Auth-Token                  User authentication token required  required
X-Image-Meta-Name             Img name                  required  required
X-Image-Meta-Id               Unique image id           **✘**     ✔
X-Image-Meta-Location         img file location @Pithos required  **✘**
X-Image-Meta-Store            Storage system            ✔         ✔
X-Image-Meta-Disk-Format      Img disk format           ✔         **✘**
X-Image-Meta-Disk_format      Img disk format           **✘**     ✔
X-Image-Meta-Container-Format Container format          ✔         **✘**
X-Image-Meta-Container_format Container format          **✘**     ✔
X-Image-Meta-Size             Size of img file          ✔         ✔
X-Image-Meta-Checksum         MD5 checksum of img file  ✔         ✔
X-Image-Meta-Is-Public        Make image public         ✔         **✘**
X-Image-Meta-Is_public        Make image public         **✘**     ✔
x-image-meta-Min-Ram          Minimum ram required (MB) **✘**     ✔
x-image-meta-Min-Disk         Maximum ram required (MB) **✘**     ✔
X-Image-Meta-Owner            Image owner               ✔         ✔
X-Image-Meta-Property-*       Property prefix           ✔         ✔         
============================= ========================= ========  ========

**X-Meta-Location** format is described at :ref:`location-ref`

**X-Image-Meta-Id** is explained at :ref:`id-ref`

**X-Image-Meta-Store** values are listed at :ref:`store-ref`

**X-Image-Meta-Disk-Format** values are listed at :ref:`disk-format-ref`

**X-Image-Meta-Container-Format** values are listed at :ref:`container-format-ref`

**X-Image-Meta-Size** is optional, but should much the actual image file size.

**X-Image-Meta-Is-Public** values are true or false (case insensitive)

**X-Image-Meta-Property-*** is used as a prefix to set custom, free-form key:value properties on an image, e.g.::

    X-Image-Meta-Property-OS: Debian Linux
    X-Image-Meta-Property-Users: Root

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           
\                           No name header
\                           Illegal header value
\                           File not found on given location
\                           Invalid size or checksum
401 (Unauthorized)          Missing or expired user token
500 (Internal Server Error) The request cannot be completed because of an internal error
501 (Not Implemented)       Location header is empty or omitted
=========================== =====================

|

The following is used when the response code is 200:

============================= ===================== ======== ======
Response Header               Description           Plankton Glance
============================= ===================== ======== ======
X-Image-Meta-Id               Unique img id         ✔        **✘**
X-Image-Meta-Name             Img name              ✔        **✘**
X-Image-Meta-Disk-Format      Disk format           ✔        **✘**
X-Image-Meta-Container-Format Container format      ✔        **✘**
X-Image-Meta-Size             Img file size         ✔        **✘**
X-Image-Meta-Checksum         Img file MD5 checksum ✔        **✘**
X-Image-Meta-Location         Pithos+ file location ✔        **✘**
X-Image-Meta-Created-At       Date of img creation  ✔        **✘**
X-Image-Meta-Deleted-At       Date of img deletion  ✔        **✘*
X-Image-Meta-Status           Img status            ✔        **✘**
X-Image-Meta-Is-Public        True if img is public ✔        **✘**
X-Image-Meta-Owner            Img owner or tentant  ✔        **✘**
X-Image-Meta-Property-*       Custom img properties ✔        **✘**
============================= ===================== ======== ======

Update an Image
---------------

In Plankton, an image can be updated either by re-registering with different metadata, or by using the request described in the present subsection.

In Glance, an update is implemented as a *PUT* request on ``/images`` URI. The method described bellow is not part of the Glance API.

====================== ====== ======== ======
URI                    Method Plankton Glance
====================== ====== ======== ======
``/images``            PUT    **✘**    ✔
``/images/<image-id>`` PUT    ✔        **✘**
====================== ====== ======== ======

The following refers only to the Plankton implementation.

**image-id** is explained at :ref:`id-ref`

|

============================= =========================
Request Header Name           Value                    
============================= =========================
X-Auth-Token                  User authentication token
X-Image-Meta-Name             New image name           
X-Image-Meta-Disk-Format      New disk format          
X-Image-Meta-Container-Format New container format     
X-Image-Meta-Status           New image status         
X-Image-Meta-Is-Public        (un)publish the image    
X-Image-Meta-Owner            Set an owner             
X-Image-Meta-Property-*       Add / modify properties  
============================= =========================

**X-Image-Meta-Disk-Format** values are listed at :ref:`disk-format-ref`

**X-Image-Meta-Container-Format** values are listed at :ref:`container-format-ref`

**X-Image-Meta-Size** is optional, but should much the actual image file size.

**X-Image-Meta-Is-Public** values are true or false (case insensitive)

**X-Image-Meta-Property-*** is used as a prefix to update image property values, or set some extra proeperties. If a registered image already contains some custom properties that are not addressed in the update request, these properties will remain untouched. For example::

    X-Image-Meta-Property-OS: Debian Linux
    X-Image-Meta-Property-Users: Root

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           
\                           Illegal header value
\                           Invalid size or checksum
401 (Unauthorized)          Missing or expired user token
404 (Not found)             Image not found
405 (Not allowed)           Current user does not have permission to change the image
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

|

The following is received when the response code is 200:

============================= =====================
Response Header               Description          
============================= =====================
X-Image-Meta-Id               Unique img id        
X-Image-Meta-Name             Img name             
X-Image-Meta-Disk-Format      Disk format          
X-Image-Meta-Container-Format Container format     
X-Image-Meta-Size             Img file size        
X-Image-Meta-Checksum         Img file MD5 checksum
X-Image-Meta-Location         Pithos+ file location
X-Image-Meta-Created-At       Date of img creation 
X-Image-Meta-Deleted-At       Date of img deletion 
X-Image-Meta-Status           Img status           
X-Image-Meta-Is-Public        True if img is public
X-Image-Meta-Owner            Img owner or tentant 
X-Image-Meta-Property-*       Custom img properties
============================= =====================

.. hint:: In Plankton, use POST to completely reset all image properties and metadata, but use PUT to update a few values without affecting the rest.

Retrieve Image Metadata
-----------------------

This request returns the metadata of an image. Images are identified by their unique image id.

In a typical scenario, client applications would query the server to `List Available Images <#id2>`_ for them and then choose one of the image ids returned.

====================== ====== ======== ======
URI                    Method Plankton Glance
====================== ====== ======== ======
``/images/<image-id>`` HEAD   ✔        ✔
====================== ====== ======== ======

**image-id** is explained at :ref:`id-ref`

|

====================  ========================= ======== =========
Request Header Name   Value                     Plankton Glance
====================  ========================= ======== =========
X-Auth-Token          User authentication token required  required
====================  ========================= ======== =========

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Image not found
405 (Not Allowed)           Access to that image is not allowed
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

|

============================= ===================== ======== ======
Response Header               Description           Plankton Glance
============================= ===================== ======== ======
X-Image-Meta-Id               Unique img id         ✔        ✔
X-Image-Meta-Location         Pithos+ file location ✔        **✘**
X-Image-Meta-URI              URI of image file     **✘**    ✔
X-Image-Meta-Name             Img name              ✔        ✔
X-Image-Meta-Disk-Format      Disk format           ✔        **✘**
X-Image-Meta-Disk_format      Disk format           **✘**    ✔
X-Image-Meta-Container-Format Container format      ✔        **✘**
X-Image-Meta-Container_format Container format      **✘**    ✔
X-Image-Meta-Size             Img file size         ✔        ✔
X-Image-Meta-Checksum         Img file MD5 checksum ✔        ✔
X-Image-Meta-Created-At       Date of img creation  ✔        **✘**
X-Image-Meta-Created_At       Date of img creation  **✘**    ✔
X-Image-Meta-Updated-At       Last modification     ✔        **✘**
X-Image-Meta-Updated_At       Last modification     **✘**    ✔
X-Image-Meta-Deleted-At       Date of img deletion  ✔        **✘**
X-Image-Meta-Deleted_At       Date of img deletion  **✘**    ✔
X-Image-Meta-Status           Img status            ✔        ✔
X-Image-Meta-Is-Public        True if img is public ✔        ✔
X-Image-Meta-Min-Ram          Minimum image RAM     **✘**    ✔
X-Image-Meta-Min-Disk         Minimum disk size     **✘**    ✔
X-Image-Meta-Owner            Img owner or tentant  ✔        ✔
X-Image-Meta-Property-*       Custom img properties ✔        ✔
============================= ===================== ======== ======

**X-Image-Created-At** is the (immutable) date of initial registration, while **X-Image-Meta-Updated-At** indicates the date of last modification of the image (if any).

**X-Image-Meta-Store** values are listed at :ref:`store-ref`

**X-Image-Meta-Disk-Format** values are listed at :ref:`disk-format-ref`

**X-Image-Meta-Container-Format** values are listed at :ref:`container-format-ref`

**X-Image-Meta-Is-Public** values are true or false (case insensitive)

**X-Image-Meta-Property-*** is used as a prefix to set custom, free-form key:value properties on an image, e.g.::

    X-Image-Meta-Property-OS: Debian Linux
    X-Image-Meta-Property-Users: Root

Example Plankton Headers response::

    x-image-meta-id: 940509eb-eb4f-496c-8443-22ffd24912e9
    x-image-meta-location: pithos://25cced7-bd53-4145-91ee-cf4737e9fb2/images/some-image.diskdump
    x-image-meta-name: Debian Desktop
    x-image-meta-disk-format: diskdump
    x-image-meta-container-format: bare
    x-image-meta-size: 3399127040
    x-image-meta-checksum: d0f28e4d72927c90eadf30917d94d0156781fe1351ed16402b538316d404
    x-image-meta-created-at: 2013-02-26 12:04:31
    x-image-meta-updated-at: 2013-02-26 12:05:28
    x-image-meta-deleted-at: 
    x-image-meta-status: available
    x-image-meta-is-public: True
    x-image-meta-owner: 25cced7-bd53-4145-91ee-cf4737e9fb2
    x-image-meta-property-partition-table: msdos
    x-image-meta-property-osfamily: linux
    x-image-meta-property-sortorder: 2
    x-image-meta-property-description: Debian 6.0.7 (Squeeze) Desktop
    x-image-meta-property-os: debian
    x-image-meta-property-users: root user
    x-image-meta-property-kernel: 2.6.32
    x-image-meta-property-root-partition: 1
    x-image-meta-property-gui: GNOME 2.30.2

Retrieve Raw Image Data
-----------------------

In **Plankton**, the raw image data is stored at a `Pithos <pithos.html>`_ server and it can be downloaded from the Pithos web UI, with a `client <https://okeanos.grnet.gr/services/pithos/>`_ or with `kamaki <http://www.synnefo.org/docs/kamaki/latest/index.html>`_. The location of an image file can be retrieved from the *X-Image-Meta-Location* header field (see `Retrieve Image Meta <#id10>`_)

In **Glance**, the raw image can be downloaded with a GET request on ``/images/<image-id>``.

List Image Memberships
----------------------

This request returns the list of users who can access an image. Plankton returns an empty list if the image is publicly accessible.

============================== ====== ======== ======
URI                            Method Plankton Glance
============================== ====== ======== ======
``/images/<image-id>/members`` GET    ✔        ✔
============================== ====== ======== ======

**image-id** is explained at :ref:`id-ref`

|

====================  ========================= ======== =========
Request Header Name   Value                     Plankton Glance
====================  ========================= ======== =========
X-Auth-Token          User authentication token required  required
====================  ========================= ======== =========

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Image not found
405 (Not Allowed)           Access to that image is not allowed
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

|

The response data is a list of users (members) who can access this image

================ ===================== ======== ======
Name             Description           Plankton Glance
================ ===================== ======== ======
member_id        uuid (user id)        ✔        ✔
can_share        Member can share img  false    ✔
================ ===================== ======== ======

**can_share** in Plankton is always false and is returned for compatibility reasons.

Example Plankton response::

    {'members': [
        {'member_id': 'th15-4-u53r-1d-fr0m-p1th05',
        'can_share': false},
        ...
    ]}

Replace a Membership List
-------------------------

This request replaces the list of users who can access a registered image. The term "replace" means that the old permission list of the image is abandoned (old permission settings are lost).

============================== ====== ======== ======
URI                            Method Plankton Glance
============================== ====== ======== ======
``/images/<image-id>/members`` PUT    ✔        ✔
============================== ====== ======== ======

**image-id** is explained at :ref:`id-ref`

|

====================  ========================= ======== =========
Request Header Name   Value                     Plankton Glance
====================  ========================= ======== =========
X-Auth-Token          User authentication token required  required
====================  ========================= ======== =========
|

Request data should be json-formated. It must consist of a *memberships* field which is a list of members with the following fields:

================ ===================== ======== ======
Name             Description           Plankton Glance
================ ===================== ======== ======
member_id        uuid (user id)        ✔        ✔
can_share        Member can share img  ignored  ✔
================ ===================== ======== ======

**can_share** is optional and ignored in Plankton.

A request data example::

    {'memberships': [
        {'member_id': 'uuid-1',
        'can_share': false},
        {'member_id': 'uuid-2'},
        ...
    ]}

|

=========================== =====================
Return Code                 Description
=========================== =====================
200 (OK)                    The request succeeded
400 (Bad Request)           Invalid format for request data
401 (Unauthorized)          Missing or expired user token
404 (Not Found)             Image not found
405 (Not Allowed)           Access to that image is not allowed
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

Add a Member to an Image
------------------------

Remove a Member from an Image
-----------------------------

List Shared Images
------------------

Index of variables
------------------

The following variables affect the behavior of many requests.

.. _id-ref:

Image ID
^^^^^^^^

The image id is a unique identifier for an image stored in Plankton or Glance.

======================= ========  ======
Image-Id                Plankton  Glance
======================= ========  ======
Automatically generated ✔         **✘**
Can be provided by user **✘**     ✔
======================= ========  ======

.. _location-ref:

Image File Location at a Pithos+ Server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To refer to a pithos location file, use the following format::

    pithos://<unique-user-id>/<container>/<object-path>

The terms unique-user-id (uuid), container and object-path are used as defined in `Pithos <pithos.html>`_ context.

.. _container-format-ref:

Container format
^^^^^^^^^^^^^^^^

===== ================================= ======== ======
Value Description                       Plankton Glance
===== ================================= ======== ======
aki   Amazon kernel image               ✔        ✔
ari   Amazon ramdisk image              ✔        ✔
ami   Amazon machine image              ✔        ✔
bare  no container or metadata envelope default  default
ovf   Open Virtualization Format        ✔        ✔
===== ================================= ======== ======

.. _disk-format-ref:

Disk format
^^^^^^^^^^^

======== ================================= ======== ======
Value    Description                       Plankton Glance
======== ================================= ======== ======
diskdump Any disk image dump               default  **✘**
extdump  EXT3 image                        ✔        **✘**
ntfsdump NTFS image                        ✔        **✘**
raw      Unstructured disk image           **✘**    ✔
vhd      (VMWare,Xen,MS,VirtualBox, a.o.)  **✘**    ✔
vmdk     Another common disk format        **✘**    ✔
vdi      (VirtualBox, QEMU)                **✘**    ✔
iso      optical disc (e.g. CDROM)         **✘**    ✔
qcow2    (QEMU)                            **✘**    ✔
aki      Amazon kernel image               **✘**    ✔
ari      Amazon ramdisk image              **✘**    ✔
ami      Amazon machine image              **✘**    ✔
======== ================================= ======== ======

.. _store-ref:

Store types
^^^^^^^^^^^

======================= ========  ======
X-Image-Meta-Store      Plankton  Glance
======================= ========  ======
pithos                  ✔         **✘**
file                    **✘**     ✔
s3                      **✘**     ✔
swift                   **✘**     ✔
======================= ========  ======