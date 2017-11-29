Upgrade to Synnefo v0.21
^^^^^^^^^^^^^^^^^^^^^^^^

Upgrade Steps
=============

The upgrade from v0.20 to v0.21 consists of the following steps:

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

The setting `CYCLADES_VM_MAX_TAGS` regards virtual machine tags, that is, tags attached to virtual machines.
This is a new feature added to the current Synnefo version.
The new setting controls the number of tags allowed per virtual machine. It defaults to 50 as per the OpenStack Compute API.
