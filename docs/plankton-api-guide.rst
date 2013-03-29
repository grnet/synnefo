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

Cross-method variables
----------------------

The following variables affect the behavior of many requests.

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

Image ReST API
--------------
================================================ ===================================== ====== ======== ======
Description                                      URI                                   Method Plankton Glance
================================================ ===================================== ====== ======== ======
`List Available Images <#id2>`_                  ``/images``                           GET    ✔        ✔
`Add or update an Image <#id3>`_                 ``/images``                           POST   ✔        ✔
`Update an Image <#id5>`_                        ``/images``                           PUT    ✔        **✘**
`List Available Images in Detail <#id6>`_        ``/images/detail``                    GET    ✔        ✔
`Retrieve Image Metadata <#id7>`_                ``/images/<img-id>``                  HEAD   ✔        ✔
`Retrieve Raw Image Data <#id8>`_                ``/images/<img-id>``                  GET    **✘**    ✔
`List Image Memberships <#id9>`_                 ``/images/<img-id>/members``          GET    ✔        ✔
`Replace a Membership List of an Image <#id10>`_ ``/images/<img-id>/members``          PUT    ✔        ✔
`Add a Member to an Image <#id11>`_              ``/images/<img-id>/members/<member>`` PUT    ✔        ✔
`Remove a Member from an Image <#id12>`_         ``/images/<img-id>/members/<member>`` DELETE ✔        ✔
`List Shared Images <#id13>`_                    ``/shared-images/<member>``           GET    ✔        ✔
================================================ ===================================== ====== ======== ======

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

===================== =========== ====== ======== ======
Description           URI         Method Plankton Glance
===================== =========== ====== ======== ======
List Available Images ``/images`` GET    ✔        ✔
===================== =========== ====== ======== ======

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

Add or update an image
----------------------

According to the Synnefo approach, this request performs two functionalities:

* registers a new image to Plankton
* commits metadata for the new image
* update the metadata of an existing image

The physical image file must be uploaded on a `Pithos+ <pithos.html>`_ server, at a space accessible by the user. The Pithos+ location of the physical file acts as a key for the image (image ids and image locations are uniquely coupled).

According to the OpenStack approach, this request performs the first two functionalities by uploading the the image data and metadata to Glance. In Glance, the update mechanism is not implemented with this specific request.

===================== =========== ====== ======== ======
Description           URI         Method Plankton Glance
===================== =========== ====== ======== ======
Add / update an image ``/images`` POST   ✔        ✔
===================== =========== ====== ======== ======

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

**X-Meta-Location** format::

    pithos://<unique-user-id>/<container>/<object-path>

The terms unique-user-id (uuid), container and object-path are used as defined in `Pithos <pithos.html>`_ context.

|

======================= ========  ======
X-Image-Meta-Id         Plankton  Glance
======================= ========  ======
Automatically generated ✔         **✘**
Can be provided by used **✘**     ✔
======================= ========  ======

|

======================= ========  ======
X-Image-Meta-Store      Plankton  Glance
======================= ========  ======
pithos                  ✔         **✘**
file                    **✘**     ✔
s3                      **✘**     ✔
swift                   **✘**     ✔
======================= ========  ======

**X-Meta-Disk-Format** values are listed at :ref:`disk-format-ref`

**X-Meta-Container-Format** values are listed at :ref:`container-format-ref`

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
X-Image-Meta-Id               Auto-generated img id ✔        **✘**
X-Meta-Image-Name             Img name              ✔        **✘**
X-Meta-image-Disk-Format      Disk format           ✔        **✘**
X-Meta-Image-Container-Format Container format      ✔        **✘**
X-Image-Meta-Size             Img file size         ✔        **✘**
X-Image-Meta-Checksum         Img file MD5 checksum ✔        **✘**
X-Image-Meta-Location         Pithos+ file location ✔        **✘**
X-Image-Meta-Created_at       Date of img creation  ✔        **✘**
X-Image-Meta-Deleted_at       Date of img deletion  ✔        **✘**
X-Image-Meta-Status           Img status            ✔        **✘**
X-Image-Meta-Is-Public        True if img is public ✔        **✘**
X-Image-Meta-Owner            Img owner or tentant  ✔        **✘**
X-Image-Meta-Property-*       Custom img properties ✔        **✘**
============================= ===================== ======== ======

Update an Image
---------------

In Plankton, the ReST API desctiption details above not only cover addition of new images, but also updating an existing one. An image is identified by its location at the Pithos server (X-Image-Meta-Location). For example, to alter the name of an image, add an image with the same X-Image-Meta-Location header but a different X-Image-Meta-Name header. An update overwrites the old values. An omission of a header option is equivalent to the removal of the corresponding property or metadata from the image, provided it is allowed for an image to exist without this specific metadatum.

Glance manages image updates by compining *PUT* with semantics similar to *POST* for the same URI. Check the `Glance documentation <http://docs.openstack.org/developer/glance/glanceapi.html#update-an-image>`_ for more details on Glance implementation.

List Available Images in Detail
-------------------------------

Lulu

Retrieve Image Metadata
-----------------------

Retrieve Raw Image Data
-----------------------

List Image Memberships
----------------------

Replace a Membership List for an Image
--------------------------------------

Add a Member to an Image
------------------------

Remove a Member from an Image
-----------------------------

List Shared Images
------------------
