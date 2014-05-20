Upgrade to Synnefo v0.16
^^^^^^^^^^^^^^^^^^^^^^^^


Upgrade Steps
=============

The upgrade to v0.16 consists in the following steps:

1. Bring down services and backup databases.

2. Upgrade packages, migrate the databases and configure settings.

3. Inspect and adjust resource limits.

4. Bring up all services.

.. warning::

    It is strongly suggested that you keep separate database backups
    for each service after the completion of each step.

1. Bring web services down, backup databases
============================================

1. All web services must be brought down so that the database maintains a
   predictable and consistent state during the migration process::

    $ service gunicorn stop
    $ service snf-dispatcher stop
    $ service snf-ganeti-eventd stop

2. Backup databases for recovery to a pre-migration state.

3. Keep the database servers running during the migration process.


2. Upgrade Synnefo and configure settings
=========================================

2.1 Install the new versions of packages
----------------------------------------

::

    astakos.host$ apt-get install \
                            python-objpool \
                            snf-common \
                            python-astakosclient \
                            snf-django-lib \
                            snf-webproject \
                            snf-branding \
                            snf-astakos-app

    cyclades.host$ apt-get install \
                            python-objpool \
                            snf-common \
                            python-astakosclient \
                            snf-django-lib \
                            snf-webproject \
                            snf-branding \
                            snf-pithos-backend \
                            snf-cyclades-app

    pithos.host$ apt-get install \
                            python-objpool \
                            snf-common \
                            python-astakosclient \
                            snf-django-lib \
                            snf-webproject \
                            snf-branding \
                            snf-pithos-backend \
                            snf-pithos-app \
                            snf-pithos-webclient

    ganeti.node$ apt-get install \
                            python-objpool \
                            snf-common \
                            snf-cyclades-gtools \
                            snf-pithos-backend \
                            snf-network

.. note::

   Make sure `snf-webproject' has the same version with snf-common

.. note::

    Installing the packages will cause services to start. Make sure you bring
    them down again (at least ``gunicorn``, ``snf-dispatcher``)

2.2 Sync and migrate the database
---------------------------------

.. note::

   If you are asked about stale content types during the migration process,
   answer 'no' and let the migration finish.

::

    astakos-host$ snf-manage syncdb
    astakos-host$ snf-manage migrate

    cyclades-host$ snf-manage syncdb
    cyclades-host$ snf-manage migrate

    pithos-host$ pithos-migrate upgrade head


3. Inspect and adjust resource limits
=====================================

Synnefo 0.16 brings significant changes at the project mechanism. Projects
are now viewed as a source of finite resources, instead of a means to
accumulate quota. They are the single source of resources, and quota are now
managed at a project/member level.

System-provided quota are now handled through special purpose
user-specific *system projects*, identified with the same UUID as the user.
These have been created during the database migration process. They are
included in the project listing with::

  snf-manage project-list --system-projects

All projects must specify quota limits for all registered resources. Default
values have been set for all resources, listed with::

  astakos-host$ snf-manage resource-list

Column `system_default` (previously known as `default_quota`) provides the
skeleton for the quota limits of user-specific system projects. Column
`project_default` is new and acts as skeleton for `applied` (non-system)
projects (i.e., for resources not specified in a project application).
Project defaults have been initialized during migration based on the system
default values: they have been set to `inf` if `system_default` is also `inf`,
otherwise set to zero.

This default, affecting all future projects, can be modified with::

  astakos-host$ snf-manage resource-modify <name> --project-default <value>

Till now a project definition contained one quota limit per resource: the
maximum that a member can get from the project. A new limit is introduced:
the grand maximum a project can provide to its members. This new project
limit is initialized during migration as `max members * member limit` (if
`max members` is not set, the double of current active members is assumed).

Existing projects can now be modified directly through the command line. In
order to change a project's resource limits, run::

  astakos-host$ snf-manage project-modify <project_uuid> --limit <resource_name> <member_limit> <project_limit>

With the new mechanism, when a new resource is allocated (e.g., a VM or a
Pithos container is created), it is also associated with a project besides
its owner. The migration process has associated existing resources with
their owner's system project. Note that users who had made use of projects to
increase their quota may end up overlimit on some resources of their system
projects and will need to *reassign* some of their reserved resources to
another project in order to overcome this restriction.

4. Bring all services up
========================

After the upgrade is finished, we bring up all services:

.. code-block:: console

    astakos.host  # service gunicorn start
    cyclades.host # service gunicorn start
    pithos.host   # service gunicorn start

    cyclades.host # service snf-dispatcher start
