Upgrade to Synnefo v0.14.6
^^^^^^^^^^^^^^^^^^^^^^^^^^

The upgrade from v0.14.2 to v0.14.6 consists of the following step:

1. Set default container quota policy to unlimited for the containers
   created prior to 0.14

2. Re-register services in astakos

1. Set default container quota policy to unlimited in old containers
====================================================================

1. In 0.14 has changed the default container quota policy and the containers
   by default have no limits in their quota. However this affects only the
   neawly created containers.
   
   In order to massively change the quota of ``pithos`` container
   (in all the accounts)::

    $ pithos-manage-accounts set-container-quota pithos 0

   In order to massively change the quota of ``trash`` container
   (in all the accounts)::
    $ pithos-manage-accounts set-container-quota trash 0

   In order to massively change the quota of ``images`` container
   (in all the accounts)::
    $ pithos-manage-accounts set-container-quota images 0

2. Re-register services in astakos
==================================

Service definitions have changed; you will thus need to register their new
version. In astakos node, run::

    astakos-host$ snf-component-register

This will detect that the Synnefo components are already registered and ask
to update the registered services. Answer positively. You need to enter the
base URL for each component; give the same value as in the initial
registration.
