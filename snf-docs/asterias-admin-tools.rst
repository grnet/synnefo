Administration Tools User's Guide
=================================

Configure kamaki
----------------

To upload, register or modify an image you will need the **kamaki** tool.
Before proceeding make sure that it is configured properly. Verify that
*image_url*, *storage_url*, *storage_account*, *storage_container* and
*token* are set as needed::

  kamaki config list

To chage a setting use ``kamaki config set``::

  kamaki config set storage_account okeanos
  kamaki config set storage_container images
  kamaki config set token ...


Upload an image
---------------

You are now ready to upload an image. You can upload it with a Pithos client
or use kamaki directly::

  kamaki store upload ubuntu.iso

You can use any Pithos client to verify that the image was uploaded correctly.


Register the image
------------------

To register an image you will need to use the full Pithos URL. To register as
a public image the one from the previous example use::

  kamaki glance register Ubuntu pithos://okeanos/images/ubuntu.iso --public

Use ``kamaki glance register`` with no arguments to see a list of available
options. A more complete example would be the following::

  kamaki glance register Ubuntu pithos://okeanos/images/ubuntu.iso --public \
      --disk-format diskdump --property kernel=3.1.2

To verify that the image was registered successfully use::

  kamaki glance list -l
