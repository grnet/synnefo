Astakos Developer Guide
=======================

Introduction
------------

Astakos is a identity management service implemented by GRNET (http://www.grnet.gr). Users can create and manage their account, invite others and send feedback for GRNET services. During the account creation the user can select against which provider wants to authenticate:

* Astakos
* Twitter
* Shibboleth

Astakos provides also an administrative interface for managing user accounts.

Astakos is build over django and extends its authentication mechanism.

This document's goals are:

* Define the Astakos ReST API that allows the GRNET services to retrieve user information via HTTP calls
* Describe the Astakos views and provide guidelines for a developer to extend them

The present document is meant to be read alongside the Django documentation. Thus, it is suggested that the reader is familiar with associated technologies.

Document Revisions
^^^^^^^^^^^^^^^^^^

=========================  ================================
Revision                   Description
=========================  ================================
0.1 (Jub 24, 2012)         Initial release.
=========================  ================================

Astakos Users and Authentication
--------------------------------

Astakos extends django User model.

Each user is uniquely identified by the ``username`` field. An astakos user instance is assigned also with a ``auth_token`` field used by the astakos clients to authenticate a user. All API requests require a token.

Logged on users can perform a number of actions:

* access and edit their profile via: ``https://hostname/im/profile``.
* change their password via: ``https://hostname/im/password``
* invite somebody else via: ``https://hostname/im/invite``
* send feedback for grnet services via: ``https://hostname/im/send_feedback``
* logout via: ``https://hostname/im/logout``

User entries can also be modified/added via the management interface available at ``https://hostname/im/admin``.

A superuser account can be created the first time you run the manage.py syncdb django command. At a later date, the manage.py createsuperuser command line utility can be used.

Astakos is also compatible with Twitter and Shibboleth (http://shibboleth.internet2.edu/). The connection between Twitter and Astakos is done by ``https://hostname/im/target/twitter/login``. The connection between Shibboleth and Astakos is done by ``https://hostname/im/target/shibboleth/login``. An application that wishes to connect to Astakos, but does not have a token, should redirect the user to ``https://hostname/im/login``.

The login URI accepts the following parameters:

======================  =========================
Request Parameter Name  Value
======================  =========================
next                    The URI to redirect to when the process is finished
renew                   Force token renewal (no value parameter)
======================  =========================

In case the user wants to authenticate via Astakos fills the login form and post it to ``https://hostname/im/local/login``.

Otherwise (the user selects a third party authentication) the login process starts by redirecting the user to an external URI (controlled by the third party), where the actual authentication credentials are entered. Then, the user is redirected back to the login URI, with various identification information in the request headers.

If the user does not exist in the database, Astakos adds the user and creates a random token. If the user exists, the token has not expired and ``renew`` is not set, the existing token is reused. Finally, the login URI redirects to the URI provided with ``next``, adding the ``user`` and ``token`` parameters, which contain the ``Uniq`` and ``Token`` fields respectively.

The Astakos API
---------------

Authenticate
^^^^^^^^^^^^

==================================== =========  ==================
Uri                                  Method     Description
==================================== =========  ==================
``https://hostname/im/authenticate`` GET        Authenticate user using token
==================================== =========  ==================

|

====================  ===========================
Request Header Name   Value
====================  ===========================
X-Auth-Token          Authentication token
====================  ===========================

Extended information on the user serialized in the json format will be returned:

===========================  ============================
Name                         Description
===========================  ============================
uniq                         User uniq identifier
auth_token                   Authentication token
auth_token_expires           Token expiration date
auth_token_created           Token creation date
===========================  ============================

Example reply:

::

  {"uniq": "admin",
  "auth_token": "0000",
  "auth_token_expires": "Tue, 11-Sep-2012 09:17:14 ",
  "auth_token_created": "Sun, 11-Sep-2011 09:17:14 "}

|

=========================== =====================
Return Code                 Description
=========================== =====================
204 (No Content)            The request succeeded
400 (Bad Request)           The request is invalid
401 (Unauthorized)          Missing token or inactive user
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================