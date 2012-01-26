Administration Tools User's Guide
=================================

Registering an Image
--------------------

To upload an image to Pithos and register it for use by Plankton, use the **image upload** command::

    snf-admin image upload Ubuntu /tmp/ubuntu.iso --public

You can additionally pass *disk_format*, *container_format* and other custom metadata::

    snf-admin image upload Ubuntu /tmp/ubuntu.iso --public --disk-format diskdump --meta kernel=2.6.42

The images are uploaded to the *images* container of the *SYSTEM_IMAGES_OWNER* user (defined in settings).

To register an image that is already stored in Pithos, use the **image register** command::

    snf-admin image register Debian pithos://okeanos/images/debian.iso dump --public

As with upload you can additionally pass custom metadata with ``--meta``.

To verify the image use **image list**:

    snf-admin image list -l a58a3cce-c938-6ef4-6b1a-529bda1e9e03


Modifying an Image
------------------

You can modify an already registered image use **image update**::

    snf-admin image update a58a3cce-c938-6ef4-6b1a-529bda1e9e03 --disk-format diskdump --name Xubuntu

To modify just the custom metadata use **image meta**::

    snf-admin image meta a58a3cce-c938-6ef4-6b1a-529bda1e9e03 OS=Linux

To verify all the metadata, use **image meta** with no arguments::

    snf-admin image meta a58a3cce-c938-6ef4-6b1a-529bda1e9e03
