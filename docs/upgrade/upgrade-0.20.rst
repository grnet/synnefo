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
