Upgrade to Synnefo v0.18.1
^^^^^^^^^^^^^^^^^^^^^^^^^^

Upgrade Steps
=============

The upgrade to v0.18 consists of the following steps:

#. Stop gunicorn in all nodes

   .. code-block:: console

      # service gunicorn stop

#. Upgrade Synnefo on all nodes to the latest version

   .. code-block:: console

      # apt-get update
      # apt-get upgrade

#. Run migrations on Astakos.

   .. code-block:: console

      astakos.host$ snf-manage migrate


   From this version on, user deactivation triggers suspension of all projects
   and project memberships related to the user. To apply this new policy to
   users that have already been deactivated, run:

   .. code-block:: console

      astakos.host$ snf-manage user-check --all-users --suspend-deactivated --noemail --fix

#. Start gunicorn

  .. code-block:: console

     # service gunicorn start


New configuration options
=========================

On the admin app, there is a new access control option regarding the new modify
email action. The action setting is named 'modify_email'. The list of user
groups defined in this have access on the modify email action.

The following line (modified accordingly) should be added on 'ADMIN_RBAC'
setting under the 'user' dictionary:

.. code-block:: console

   'modify_email': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
