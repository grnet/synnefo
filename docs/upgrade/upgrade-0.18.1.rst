Upgrade to Synnefo v0.18.1
^^^^^^^^^^^^^^^^^^^^^^^^^^

Upgrade Steps
=============

The upgrade from v0.17 to v0.18.1 consists of the following steps:

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


#. Run migrations on Astakos.

   .. code-block:: console

      astakos.host$ snf-manage migrate


   From this version on, user deactivation triggers suspension of all projects
   and project memberships related to the user. To apply this new policy to
   users that have already been deactivated, run:

   .. code-block:: console

      astakos.host$ /usr/lib/astakos/tools/fix_deactivated_users --all-users --noemail --fix

#. Restart services

  .. code-block:: console

     $ service gunicorn start
     $ service snf-dispatcher start
     $ service snf-ganeti-eventd start


New configuration options
=========================

On the admin app, there is a new access control option regarding the new modify
email action. The action setting is named 'modify_email'. The list of user
groups defined in this have access on the modify email action.

The following line (modified accordingly) should be added on 'ADMIN_RBAC'
setting under the 'user' dictionary:

.. code-block:: console

   'modify_email': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
