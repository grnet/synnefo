.. _pithos:

File Storage Service (pithos+)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pithos+ is the synnefo File Storage Service and implements the OpenStack Object
Storage API + synnefo extensions.


Introduction
============

Pithos is a storage service implemented by GRNET (http://www.grnet.gr). Data is
stored as objects, organized in containers, belonging to an account. This
hierarchy of storage layers has been inspired by the OpenStack Object Storage
(OOS) API and similar CloudFiles API by Rackspace. The Pithos API follows the
OOS API as closely as possible. One of the design requirements has been to be
able to use Pithos with clients built for the OOS, without changes.

However, to be able to take full advantage of the Pithos infrastructure, client
software should be aware of the extensions that differentiate Pithos from OOS.
Pithos objects can be updated, or appended to. Pithos will store sharing
permissions per object and enforce corresponding authorization policies.
Automatic version management, allows taking account and container listings back
in time, as well as reading previous instances of objects.

The storage backend of Pithos is block oriented, permitting efficient,
deduplicated data placement. The block structure of objects is exposed at the
API layer, in order to encourage external software to implement advanced data
management operations.


Pithos Users and Authentication
===============================

In Pithos, each user is uniquely identified by a token. All API requests
require a token and each token is internally resolved to an account string. The
API uses the account string to identify the user's own files, thus whether a
request is local or cross-account.

Pithos does not keep a user database. For development and testing purposes,
user identifiers and their corresponding tokens can be defined in the settings
file. However, Pithos is designed with an external authentication service in
mind. This service must handle the details of validating user credentials and
communicate with Pithos via a middleware software component that, given a
token, fills in the internal request account variable.

Client software using Pithos, if not already knowing a user's identifier and
token, should forward to the ``/login`` URI. The Pithos server, depending on
its configuration will redirect to the appropriate login page.

The login URI accepts the following parameters:

======================  =========================
Request Parameter Name  Value
======================  =========================
next                    The URI to redirect to when the process is finished
renew                   Force token renewal (no value parameter)
force                   Force logout current user (no value parameter)
======================  =========================

When done with logging in, the service's login URI should redirect to the URI
provided with ``next``, adding ``user`` and ``token`` parameters, which contain
the account and token fields respectively.

A user management service that implements a login URI according to these
conventions is Astakos.


Pithos+ Architecture
====================
