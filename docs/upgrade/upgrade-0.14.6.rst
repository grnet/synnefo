Upgrade to Synnefo v0.14.6
^^^^^^^^^^^^^^^^^^^^^^^^^^

The upgrade from v0.14.2 to v0.14.6 consists of the following steps:

1. Set default container quota policy to unlimited for the containers
   created prior to 0.14

2. Re-register services in astakos

1. Set default container quota policy to unlimited in old containers
====================================================================

1. The default policy for container quota has changed in 0.14. Containers no
   longer have quota limits. However, this affects only newly created
   containers.
   
   To massively change the quota of the ``pithos`` container
   for all accounts, run::

    $ pithos-manage-accounts set-container-quota pithos 0

   To massively change the quota of the ``trash`` container
   for all accounts, run::
    $ pithos-manage-accounts set-container-quota trash 0

   To massively change the quota of the ``images`` container
   for all accounts, run::
    $ pithos-manage-accounts set-container-quota images 0

2. Re-register services in astakos
==================================

Service definitions have changed; you will thus need to register their new
version. On the astakos node, run::

    astakos-host$ snf-component-register

This will detect that the Synnefo components are already registered and ask
to update the registered services. Answer positively. You need to enter the
base URL for each component; give the same value as in the initial
registration.
