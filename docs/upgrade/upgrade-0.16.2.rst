Upgrade to Synnefo v0.16.2
^^^^^^^^^^^^^^^^^^^^^^^^^^

Since Synnefo v0.16.2 is mostly a bug fix version, the downtime required for
the upgrade should be minimal. Following the usual process, bring the services
down and upgrade the packages. Before bringing the services back up, you should
run `snf-manage migrate` on the astakos node, in order to fix the quotas of
users enrolled but not accepted in projects, which might be out-of-sync.
