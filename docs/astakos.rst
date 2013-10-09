.. _astakos:

Identity Management Service (Astakos)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Astakos is the Identity management component which provides a common user base
to the rest of Synnefo. Astakos handles user creation, user groups, resource
accounting, quotas, projects, and issues authentication tokens used across the
infrastructure. It supports multiple authentication methods:

 * local username/password
 * LDAP / Active Directory
 * SAML 2.0 (Shibboleth) federated logins
 * Google
 * Twitter
 * LinkedIn

Users can add multiple login methods to a single account, according to
configured policy.

Astakos keeps track of resource usage across Synnefo, enforces quotas, and
implements a common user dashboard. Quota handling is resource type agnostic:
Resources (e.g., VMs, public IPs, GBs of storage, or disk space) are defined by
each Synnefo component independently, then imported into Astakos for accounting
and presentation.

Astakos runs at the cloud layer and exposes the OpenStack Keystone API for
authentication, along with the Synnefo Account API for quota, user group and
project management.

Please also see the :ref:`Admin Guide <admin-guide>` for more information and the
:ref:`Installation Guide <quick-install-admin-guide>` for installation instructions.
