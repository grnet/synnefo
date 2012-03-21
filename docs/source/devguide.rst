Astakos Developer Guide
=======================

Introduction
------------

Astakos serves as the point of authentication for GRNET (http://www.grnet.gr) services. It is a platform-wide service, allowing users to register, login, and keep track of permissions.

Users in astakos can be authenticated via several identity providers:

* Local
* Twitter
* Shibboleth

It provides also a command line tool for managing user accounts.

It is build over django and extends its authentication mechanism.

This document's goals are:

* present the overall architectural design.
* provide basic use cases.
* describe the APIs to the outer world.
* document the views and provide guidelines for a developer to extend them.

The present document is meant to be read alongside the Django documentation (https://www.djangoproject.com/). Thus, it is suggested that the reader is familiar with associated technologies.

Document Revisions
^^^^^^^^^^^^^^^^^^

=========================  ================================
Revision                   Description
=========================  ================================
0.1 (Feb 10, 2012)         Initial release.
=========================  ================================

Overview
--------

Astakos service co-ordinates the access to resources (and the subsequent permission model) and acts as the single point of registry and entry to the GRNET cloud offering, comprising of Cyclades and Pithos subsystems.

It also propagates the user state to the Aquarium pricing subsystem.

.. image:: images/~okeanos.jpg

Registration Use Cases
----------------------

The following subsections describe two basic registration use cases. All the registration cases are covered in :ref:`registration-flow-label`

Invited user
^^^^^^^^^^^^

A registered ~okeanos user, invites student Alice to subscribe to ~okeanos services. Alice receives an email and through a link is navigated to Astakos's signup page. The system prompts her to select one of the available authentication mechanisms (Shibboleth, Twitter or local authentication) in order to register to the system. Alice already has a Shibboleth account so chooses that and then she is redirected to her institution's login page. Upon successful login, her account is created.

Since she is invited his account is automaticaly activated and she is redirected to Astakos's login page. As this is the first time Alice has accessed the system she is redirected to her profile page where she can edit or provide more information.

Not invited user
^^^^^^^^^^^^^^^^

Tony while browsing in the internet finds out about ~okeanos services. He visits the signup page and since his has already a twitter account selects the twitter authentication mechanism and he is redirected to twitter login page where he is promted to provide his credentials. Upon successful login, twitter redirects him back to the Astakos and the account is created.

Since his not an invited user his account has to be activated from an administrator first, in order to be able to login. Upon the account's activation he receives an email and through a link he is redirected to the login page.

Authentication Use Cases
------------------------

Cloud service user
^^^^^^^^^^^^^^^^^^

Alice requests a specific resource from a cloud service ex. Pithos. In the request supplies the `X-Auth-Token`` to identify whether she is eligible to perform the specific task. The service contacts Astakos through its ``/im/authenticate`` api call (see :ref:`authenticate-api-label`) providing the specific ``X-Auth-Token``. Astakos checkes whether the token belongs to an active user and it has not expired and returns a dictionary containing user related information. Finally the service uses the ``uniq`` field included in the dictionary as the account string to identify the user accessible resources. 

.. _registration-flow-label:

Registration Flow
-----------------

.. image:: images/signup.jpg
    :scale: 100%

Login Flow
----------
.. image:: images/login.jpg
    :scale: 100%

.. _authentication-label:

Astakos Users and Authentication
--------------------------------

Astakos incorporates django user authentication system and extends its User model.

Since username field of django User model has a limitation of 30 characters, AstakosUser is **uniquely** identified by the ``email`` instead. Therefore, ``astakos.im.authentication_backends.EmailBackend`` is served to authenticate a user using email if the first argument is actually an email, otherwise tries the username.

A new AstakosUser instance is assigned with a uui as username and also with a ``auth_token`` used by the cloud services to authenticate the user. ``astakos.im.authentication_backends.TokenBackend`` is also specified in order to authenticate the user using the email and the token fields.

Logged on users can perform a number of actions:

* access and edit their profile via: ``/im/profile``.
* change their password via: ``/im/password``
* invite somebody else via: ``/im/invite``
* send feedback for grnet services via: ``/im/send_feedback``
* logout (and delete cookie) via: ``/im/logout``

User entries can also be modified/added via the ``snf-manage activateuser`` command.

A superuser account can be created the first time you run the ``manage.py syncdb`` django command and then loading the extra user data from the ``admin_user`` fixture. At a later date, the ``manage.py createsuperuser`` command line utility can be used (as long as the extra user data for Astakos is added with a fixture or by hand).

Internal Astakos requests are handled using cookie-based django user sessions.

External systems in the same domain can delgate ``/login`` URI. The server, depending on its configuration will redirect to the appropriate login page. When done with logging in, the service's login URI should redirect to the URI provided with next, adding user and token parameters, which contain the email and token fields respectively.

The login URI accepts the following parameters:

======================  =========================
Request Parameter Name  Value
======================  =========================
next                    The URI to redirect to when the process is finished
renew                   Force token renewal (no value parameter)
force                   Force logout current user (no value parameter)
======================  =========================

External systems outside the domain scope can acquire the user information by a cookie set identified by ASTAKOS_COOKIE_NAME setting.

Finally, backend systems having acquired a token can use the :ref:`authenticate-api-label` api call from a private network or through HTTPS.

The Astakos API
---------------

.. _authenticate-api-label:

Authenticate
^^^^^^^^^^^^

Authenticate API requests require a token. An application that wishes to connect to Astakos, but does not have a token, should redirect the user to ``/login``. (see :ref:`authentication-label`)

==================== =========  ==================
Uri                  Method     Description
==================== =========  ==================
``/im/authenticate`` GET        Authenticate user using token
==================== =========  ==================

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
username                     User uniq identifier
uniq                         User email (uniq identifier used by Astakos)
auth_token                   Authentication token
auth_token_expires           Token expiration date
auth_token_created           Token creation date
has_credits                  Whether user has credits
has_signed_terms             Whether user has aggred on terms
===========================  ============================

Example reply:

::

  {"username": "4ad9f34d6e7a4992b34502d40f40cb",
  "uniq": "papagian@example.com"
  "auth_token": "0000",
  "auth_token_expires": "Tue, 11-Sep-2012 09:17:14 ",
  "auth_token_created": "Sun, 11-Sep-2011 09:17:14 ",
  "has_credits": false,
  "has_signed_terms": true}

|

=========================== =====================
Return Code                 Description
=========================== =====================
204 (No Content)            The request succeeded
400 (Bad Request)           The request is invalid
401 (Unauthorized)          Missing token or inactive user or penging approval terms
500 (Internal Server Error) The request cannot be completed because of an internal error
=========================== =====================

Get Services
^^^^^^^^^^^^

Returns a json formatted list containing information about the supported cloud services.

==================== =========  ==================
Uri                  Method     Description
==================== =========  ==================
``/im/get_services`` GET        Get cloud services
==================== =========  ==================

Example reply:

::

[{"url": "/", "icon": "home-icon.png", "name": "grnet cloud", "id": "cloud"},
 {"url": "/okeanos.html", "name": "~okeanos", "id": "okeanos"},
 {"url": "/ui/", "name": "pithos+", "id": "pithos"}]
 
Get Menu
^^^^^^^^

Returns a json formatted list containing the cloud bar links. 

==================== =========  ==================
Uri                  Method     Description
==================== =========  ==================
``/im/get_menu``     GET        Get cloud bar menu
==================== =========  ==================

|

======================  =========================
Request Parameter Name  Value
======================  =========================
location                Location to pass in the next parameter
======================  =========================

Example reply if request user is not authenticated:

::

[{"url": "/im/login?next=", "name": "login..."}]

Example reply if request user is authenticated:

[{"url": "/im/profile", "name": "spapagian@grnet.gr"},
 {"url": "/im/profile", "name": "view your profile..."},
 {"url": "/im/password", "name": "change your password..."},
 {"url": "/im/feedback", "name": "feedback..."},
 {"url": "/im/logout", "name": "logout..."}]




