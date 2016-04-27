Upgrade to Synnefo v0.17next
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Upgrade Steps
=============

The upgrade to v0.17next consists of the following steps:

0. Install the latest Synnefo, Archipelago and Ganeti packages.

1. Run migrations on Astakos.


0. Install packages
===================

TODO

1. Run migrations on Astakos
============================

::
    astakos.host$ snf-manage migrate

From this version, user deactivation triggers suspension of all projects and
project memberships related to the user. To apply this new policy to users
that have already been deactivated, run::

    astakos.host$ snf-manage user-check --all-users --suspend-deactivated --fix

