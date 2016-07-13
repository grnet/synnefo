Upgrade to Synnefo v0.18rc1
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Upgrade Steps
=============

The upgrade to v0.18rc1 consists of the following steps:

#. Upgrade Synnefo on all nodes to the latest version (0.18rc1)

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

      astakos.host$ snf-manage user-check --all-users --suspend-deactivated --fix

