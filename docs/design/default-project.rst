Design document for default project (tenant) per user
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This document presents the proposed design for having a default project per
user that is used for assigning new resources (VMs, disks, IPs, etc)
when a project is not explicitly provided with a service call.

Motivation
==========

A default project per user is one easy way to solve an existing incompatibility
with OpenStack tools that forbids their use in the majority of cases.
In brief, OpenStack tools require a suitable tenant or project id for
creating new resources on them.
However, when Synnefo is not provided with a project id, it attempts to create
resources on a user's system project, which many times has insufficient quotas.
The problem is further explained below.

Current state and shortcomings
==============================

In keystone v2 each authentication token is associated with a specific
tenant/project. When a token is authenticated by a service, the tenant is
returned and the service can create the resources on the specified tenant.

Contrary, in Synnefo a user holds a single token and the tenant/project
selection is exposed in the services' API. If a project is not supplied, then
the resource is assigned to the user's system project by default. This way,
since Openstack's API is incompatible with this, Openstack tools are restricted
to creating resources only to the user's system project, which may not even
have enough quotas.

Proposed changes
================

- Add an API call that makes a project the default to assign
  new resources when they are created without supplying a project id.
- Relate a user's token with the default project to assign resources.
- Create resources on the default project when they are created without
  supplying a project id.
- Reset a user's default project to the user's base project when the user
  leaves the project, the user is removed, or the project is terminated.
- Extend kamaki to allow users to a) set a project for assigning new
  resources by default and b) see which project is the default.
- Extend snf-manage Astakos commands to be able to set and see a user's default
  project.

Implementation details
======================

- Create a new API call that sets a user's default project

  The main action of the new call is to relate the project id of the
  specified project with the user's token in Astakos database.
  The new API call sits under the hierarchy of user account-related URL
  endpoints with the form `myaccount/default_project`.
  Internally, the requested action for the user is validated in
  `im/user_logic.py`. In addition, the provided
  project's state and the user's membership in the project are checked with
  `im/functions:validate_project_member_state`. If anything goes wrong
  with these checks an appropriate exception is raised.
  Otherwise, the user's default project is recorded within
  `im/user_logic.py:set_default_project` by setting the new field
  `default_project` of the AstakosUser model to the project's uuid.
  The `default_project` is a free-form project uuid. The default project
  is initialised as NULL, but it is set to a new user's base/system project 
  as soon as the base project is enabled in `im/functions:enable_base_project`.
  A data migration takes care of setting the default project for existing
  users to their uuid. As a migration it depends on a schema migration that
  adds the `default_project` field to the AstakosUser model.

- Make Astakos return the project id of the default project with the
  authentication response and assign it to the project id argument of a
  service call when it is empty.

  The authentication response is prepared in function `authenticate()`
  of `astakos.api.tokens`. There we have as tenant in the response, i.e.
  `d['access']['token']['tenant']['id']`, the user's default project.
  The default project is now accessible in service calls through the
  credentials object. Specifically, the default project is now part of
  the Credentials object prepared in the `api_method` decorator function
  located in `snf-django-lib/snf_django/lib/api/__init__.py`. When a service
  call that creates resources does not include a project id, the user's
  default project, i.e. the request's tenant id, is assigned. The service
  calls of interest are create server, create network, create floating ip,
  and create volume (`volume/views.py`) in Cyclades.
  In addition, the `logic/networks:create()` has been modified to carry a
  Credentials object instead of a user's uuid as first argument in order to
  be able to assign `Credentials.default_project` to the project argument
  when its value is set to `None`.

- Reset a user's default project

  This is required in the following circumestances:

  - when a user leaves a project that she has specified as default
  - when a user is removed from a project that she has specified as default
  - when a project is terminated and it corresponds to the default project
    of any project members

  Reset means that the `default_project` field is assigned the user's uuid, that
  is the user's base/system project uuid.
  For member removal or leave, the default_project field is reset within
  `ProjectMembership.perform_action()` when a member's state is set to REMOVED.
  For project termination, `default_project` is reset within
  `Project.terminate()`. The default project field is checked for each project
  member and is set to the member's uuid if it corresponds to the uuid of the
  project being terminated.

- Extend `snf-manage` Astakos commands to be able to set a user's default
  project

  A new sub-command

  `snf-manage user-modify <user_id> --set-default-project <project_id>`

  has been added to allow setting a user's default project.
  To be able to observe the effect, `snf-manage user-show` has been extended
  to present a user's default project.

- Extend kamaki to allow users to set a project for assigning new
  resources by default

  The command is implemented as a user action and is invoked as
  follows:

  `kamaki user setdefaultproject <project_id>`

  Implementation-wise, adding a new function in
  `astakosclient/astakosclient/__init_.py` is required in order to
  communicate the kamaki command to Astakos. The new function called
  `set_default_project` makes a PUT request to the corresponding URL endpoint
  in Astakos, that is `/myaccount/default_project`.
  Users are able to view their default project with the `kamaki user info`
  command after a minimal modification to the corresponding kamaki client
  command that leverages the JSON response cached from authentication calls.

Interaction between OpenStack clients and Synnefo
=================================================

There are basic differences in the way that an OpenStack cloud and Synnefo
a) authenticate users and b) handle requests for creating new resources.

An OpenStack cloud stores a token for each tenant/project. When a user
authenticates she provides a token that corresponds to a tenant/project she
participates in. If a request for creating new resources is made next, the
OpenStack cloud assigns the new resources to the tenant specified in the
authentication request without expecting a tenant identifier in the request for
creating new resources.
OpenStack clients function based on these principles. They communicate a token
for a tenant on behalf of a user in an authentication request and do not
include a tenant identifier in a request for creating new resources.

Synnefo, on the other hand, does not support token per tenant. On
authentication it requires user credentails (username, password) and does not
take into account a tenant name supplied with the authentication request (in
fact, if a tenant name is supplied, it should correspond to the user's
authentication token otherwise Synnefo aborts the request with a bad request
response). Instead, Synnefo expects the client to specify the tenant by a
Synnefo-specific parameter in an API call that creates new resources. If that
parameter is not specified, then Synnefo assigns new resources to the user's
default project.

To conclude, since OpenStack clients cannot explicitly identify the tenant in
requests for creating new resources with Synnefo, the only way to specify a
tenant is by having stated a user's default project.

Testing details
===============

We tested the changes in the following ways.

- Extend `snf-burnin` tests
  
  For `snf-burnin` we extend the `QuotasTestSuite` and the `AstakosTestSuite`.

  For the `QuotasTestSuite`, we first created a second project for
  default user (`user@synnefo.org`) so that project tests (`QuotasTestSuite`)
  can run. The second project (the first is the system or base one)
  should have at least the following resources assigned to it:

  - 2 VMs
  - 2 CPUs
  - 1 GB RAM
  - 4 GB hard disk
  - 2 floating IPs

  The project can be created through the UI with the default user
  (user@synnefo.org) and can be activated from the CI's cli with the command
  `snf-manage project-control --approve <application id>`.
  The application id can be retrieved with the command `snf-manage
  project-list`.
  Continuing with test preparation, `snf-burnin`'s common test functions
  (utilities) were extended (`common.py:_get_default_project()`) for getting
  a user's default project from `astakos.authenticate()` and updated
  (`cyclades_common.py`) to assign as project_id a user's default project
  instead of a user's uuid when a project id was not specified in a
  service call. The assigned project id was only used to
  check quotas within `_create_server()`, `_create_network()`, and
  `_create_floating_ip()` that wrap service calls (after invoking the service
  calls).
  The project tests were re-organised to test the following scenarios.

  - Create a server (after setting the second project as default) without
    explicitly specifying a project and check that the resources are assigned
    to the user's default project.
  - Create a server in a project explicitly specified
    and check that the resources are assigned to the specified project
    (the second one) even though the user's base/system project has been set
    as default.

  For the AstakosTestSuite, we have written three tests where:

  - the base project is set as the default
  - an invalid project is specified to be the default
  - valid projects (let aside the base/system one) are set as default

- Extend the kamaki Astakos client unit tests

  A new test has been added in `kamaki/kamaki/clients/astakos/test.py` that
  tests whether a `set_default_project` call to the Astakos client
  (astakosclient) results in expected calls and output.

- Extend the user-related Astakos unit tests at the API level and logic level.

  At the API level the tests, which are located in `im/tests/api.py`,
  evaluate the `set_default_project` user API call in the following
  circumstances:

  - unauthorised users
  - rejected users
  - invalid projects
  - valid projects (the base/system one)
  The tests' full name is `cyclades.astakos.im.tests:UserAPITest`

  At the logic level the tests, which are located in `im/tests/user_logic.py`,
  evaluate the `set_default_project` user logic call in the following
  circumstances:

  - wrong user states and invalid projects
  - valid projects (the base/system one)
  The tests' full name is
  `cyclades.astakos.im.tests:UserAPITest:TestUserActions`

  The project-related tests located in `im/tests/projects.py` have also been
  extended in order to test whether the `default_project` field is reset
  to a member's uuid when the project is terminated or when the member is
  removed from the project.

- Run the tests that create resources and check that they run OK.
  These tests are:

  - `cyclades.synnefo.api.tests:ServerCreateAPITest`
  - `cyclades.synnefo.logic.tests:ServerCreationTest`
  - `cyclades.synnefo.api.tests:NetworkTest.test_create`
  - `cyclades.synnefo.logic.tests:NetworkTest`
  - `cyclades.synnefo.logic.tests:IPTest.test_create`

  We updated the network tests (`logic/tests/networks.py`) to call
  logic.networks.create() with a Credentials object instead of a user's uuid.

- Run all unit tests to check for side effects.

Future work
===========

