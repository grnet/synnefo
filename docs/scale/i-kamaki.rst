.. _i-kamaki:

Synnefo
-------


:ref:`synnefo <i-synnefo>` ||
:ref:`ns <i-ns>` ||
:ref:`apt <i-apt>` ||
:ref:`mq <i-mq>` ||
:ref:`db <i-db>` ||
:ref:`gunicorn <i-gunicorn>` ||
:ref:`apache <i-apache>` ||
:ref:`webproject <i-webproject>` ||
:ref:`astakos <i-astakos>` ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
kamaki ||
:ref:`backends <i-backends>`

kamaki Setup
++++++++++++

The following apply to ``client`` node. Here we install a command line tool
that the end-user can use instead of web UI. Prerequisites are that the client
node can connect to synnefo nodes by using their FQDN and that the user has
already aquired an AUTH_TOKEN and UUID from his/her profile page after signing
in.

Install the corresponding package:

.. code-block:: console

    # apt-get install kamaki

and build the correct config file:

.. code-block:: console

    # kamaki config set astakos.url "https://accounts.example.com"
    # kamaki config set compute.url "https://cyclades.example.com/api/v1.1"
    # kamaki config set image.url "https://cyclades.example.com/image"
    # kamaki config set store.enable on
    # kamaki config set store.pithos_extensions on
    # kamaki config set store.url "https://pithos.example.com/v1"
    # kamaki config set store.account UUID

    # kamaki config set global.token AUTH_TOKEN


Please download a Debian Base image from our repo:


.. code-block:: console

    # wget https://pithos.okeanos.grnet.gr/public/66ke3 -O /tmp/debian_base.diskdump

create a container in pithos, upload it:

.. code-block:: console

   # kamaki store create images
   # kamaki store upload --container images /tmp/debian_base.diskdump debian_base.diskdump

and register it with Cyclades:

.. code-block:: console

   # kamaki image register "Debian Base"  pithos://user@example/images/debian_base.diskdump \
                    --disk-format=diskdump \
                    --property OSFAMILY=linux \
                    --property ROOT_PARTITION=1 \
                    --property description="Debian Squeeze Base System" \
                    --property size=450M \
                    --property kernel=2.6.32 \
                    --property GUI="No GUI" \
                    --property sortorder=1 \
                    --property USERS=root \
                    --property OS=debian \
                    --public

Test your Setup:
++++++++++++++++

.. code-block:: console

   # kamaki store list
   # kamaki image list

And visit https://cyclades.example.com/ui/ and try to create a VM with the registered image
or visit https://pithos.example.com/ui/ and see your uploaded image.
