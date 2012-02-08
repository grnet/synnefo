Administration Tools User's Guide
=================================

Configure kamaki
----------------

To upload, register or modify an image you will need the **kamaki** tool.
Before proceeding make sure that it is configured properly. Verify that
*image_url*, *storage_url*, and *token* are set as needed:

.. code-block:: console

  kamaki config list

To chage a setting use ``kamaki config set``:

.. code-block:: console

  kamaki config set image_url https://cyclades.example.com/plankton
  kamaki config set storage_url https://pithos.example.com/v1
  kamaki config set token ...


Upload an image
---------------

As a shortcut, you can configure a default account and container that will be
used by the ``kamaki store`` commands:

.. code-block:: console

  kamaki config set storage_account images@example.com
  kamaki config set storage_container images

If the container does not exist, you will have to create it before uploading
any images:

.. code-block:: console

  kamaki store create images

You are now ready to upload an image. You can upload it with a Pithos client
or use kamaki directly:

.. code-block:: console

  kamaki store upload ubuntu.iso

You can use any Pithos client to verify that the image was uploaded correctly.
The full Pithos URL for the previous example will be
``pithos://images@example.com/images/ubuntu.iso``.


Register the image
------------------

To register an image you will need to use the full Pithos URL. To register as
a public image the one from the previous example use:

.. code-block:: console

  kamaki glance register Ubuntu pithos://images@example.com/images/ubuntu.iso --public

The ``--public`` flag is important, if missing the registered image will not
be listed by ``kamaki glance list``.

Use ``kamaki glance register`` with no arguments to see a list of available
options. A more complete example would be the following:

.. code-block:: console

  kamaki glance register Ubuntu pithos://images@example.com/images/ubuntu.iso \
      --public --disk-format diskdump --property kernel=3.1.2

To verify that the image was registered successfully use:

.. code-block:: console

  kamaki glance list -l
