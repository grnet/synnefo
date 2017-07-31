Upgrade to Synnefo v0.20
^^^^^^^^^^^^^^^^^^^^^^^^

Upgrade Steps
=============

The upgrade from v0.19 to v0.20 consists of the following steps:

#. Bring down services::

    $ service gunicorn stop
    $ service snf-dispatcher stop
    $ service snf-ganeti-eventd stop

#. Upgrade Synnefo on all nodes to the latest version::

    astakos.host$ apt-get install \
                            snf-common \
                            python-astakosclient \
                            snf-django-lib \
                            snf-webproject \
                            snf-branding \
                            snf-astakos-app

    cyclades.host$ apt-get install \
                            snf-common \
                            python-astakosclient \
                            snf-django-lib \
                            snf-webproject \
                            snf-branding \
                            snf-pithos-backend \
                            snf-cyclades-app

    pithos.host$ apt-get install \
                            snf-common \
                            python-astakosclient \
                            snf-django-lib \
                            snf-webproject \
                            snf-branding \
                            snf-pithos-backend \
                            snf-pithos-app \
                            snf-ui-app

    ganeti.node$ apt-get install \
                            snf-common \
                            snf-cyclades-gtools \
                            snf-pithos-backend


#. Run migrations on [...].

   .. code-block:: console

      host$ snf-manage migrate


#. Restart services

  .. code-block:: console

     $ service gunicorn start
     $ service snf-dispatcher start
     $ service snf-ganeti-eventd start


New configuration options
=========================
The settings `SNF_MANAGE_USER`, `SNF_MANAGE_GROUP` control the user/group
snf-manage runs as. They default to `synnefo`:`synnefo`.

.. warning:

    On all nodes `snf-manage` has been executed, the `commands`
    directory under `/var/log/synnefo` should be assigned to the same user/group
    set on the `SNF_MANAGE_USER`:`SNF_MANAGE_GROUP` settings.

Rescue Mode for Virtual Machines
""""""""""""""""""""""""""""""""

A feature for rescuing (booting with a different image) VMs has been added. In
order to perform this action, at least one rescue image needs to be active in
the cyclades host. The rescue image can be either an HTTP link to an iso or a
file under the directory configured by the `RESCUE_IMAGE_PATH` setting.

#. Create HTTP Rescue Image::

    $ snf-manage rescue-image-create \
                                --name "My Rescue Image"
                                --location "http://some.link/to.iso"
                                --default True

The above command will create a new image will be used by default when a rescue
action is initiated.

#. Create Plain File Rescue Image::

    # If not already created
    ganeti.node$ mkdir /usr/share/synnefo/rescue-images
    ganeti.node$ mv /path/to/some/image.iso \
                      /usr/share/synnefo/rescue-images/my_image.iso

    $ snf-manage rescue-image-create \
                            --name "My File Rescue Image"
                            --location "my_image.iso"
                            --location-type file
                            --default True

The directory of the rescue images can contain any number of nested directories
as long as the location set accordingly while creating the image.

In order to enable rescue mode (which is disabled by default) the
RESCUE_ENABLED setting must be set to False.
