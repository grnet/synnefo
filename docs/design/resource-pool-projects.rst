Resource-pool projects
^^^^^^^^^^^^^^^^^^^^^^

This document describes the current state of the quota and projects system,
and proposes a new design for projects that would function as resource
pools. It sketches implementation details and migration concerns.

Current state and shortcomings
==============================

Each Synnefo user is granted quota for several resources. These quota
originate from two different sources: the system and projects. By default
a user holds so-called base quota granted by the system upon activation;
base quota can be customized per user. When a user joins a project,
resources offered by the project add up to the existing quota, increasing
the total amount of resources one can reserve.

This design fails to associate an actual (reserved) resource (e.g. VM) with
a particular project. There is no way to tell which project a resource
originates from and is thus not possible to employ any targeted policy when
a user leaves a project, such as reclaiming the granted resource. It is also
not possible to employ more advanced access control on resources, such as
sharing VMs among members of a project.

Proposed changes
================

We will alter project semantics so that a project is viewed as a pool of
finite resources. Each project member can reserve a portion of these
resources up to a specified limit. Each actual resource (e.g. VM) is
associated with a particular project. Admission of a user to a project will
no more result in increasing the user's existing overall quota, but in
defining new project-specific quota for the user.

A project defines a pair of limits for each resource that it grants (e.g.
cyclades.vm): project-level limit and member-level limit; The former is the
total amount of a resource that this project can grant; the latter is the
maximum amount that an individual user (project member) can reserve and
cannot exceed the former. A limit on the number of members allowed is still
enforced.

Projects will be the sole source of resources. Current base quota offered to
users by the system will be expressed in terms of special-purpose *system*
projects. Due to the central role that projects now acquire, we will alter
the project schema to facilitate project creation and modification without
the extra overhead of submitting and approving applications.

Implementation details
======================

Project-related quota holdings
------------------------------

The Quotaholder is responsible to record all resource allocations and
deallocations, and enforce the limits. It keeps counters of the following
structure:
 * resource: the resource name (e.g. cyclades.vm)
 * holder: the entity holding the resource (user or project)
 * source: the origin of the resource; a user-holder reserves from a
   project, a project is a top-level entity and reserves from nowhere (None)
 * limit: maximum allowed allocation (an integer)
 * usage: current allocation (an integer)

[Due to the transactional nature of the mechanism, there are actually two
usage fields (usage_min and usage_max). Details are beyond the scope of
this document.]

Creation of a new project triggers the creation of counters like::

  resource      holder              source   limit   usage
  ------------|-------------------|--------|-------|------
  cyclades.vm   project:projectID   None     50      0

When a user is admitted in a project, counters are created like::

  resource      holder          source              limit   usage
  ------------|---------------|-------------------|-------|------
  cyclades.vm   user:userUUID   project:ProjectID   5       0

Note that the two types of holders (and sources) are made distinguishable with
a prefix: ``user:`` or ``project:``.

When a user leaves a project, the latter limit is set to zero. This results
in the project-specific user quota being over limit and prohibits any
further allocation that would increase this counter. When a project
is deactivated, the limit of both types of counters is set to zero.
No user can perform any allocation related to this project. However, the
holdings cannot be deleted as long as a non-zero usage is recorded.
Deallocation is always allowed as long as usage does not fall below zero.
Counters with zero usage and limit could by garbage collected by Astakos, if
needed.

System projects
---------------

For reasons of uniformity, we replace the base quota mechanism with projects.
In a similar vein to OpenStack tenants, we define new user-specific *system*
projects to account for the base quota for each user. These projects should
be clearly associated with a single user, restrict join/leave actions and
specify the quota granted by the system. When a new user is created,
their system project will be automatically created and linked back to the user.
User activation will trigger project activation, granting the default resource
quota. These projects will have no owner, marked thusly as `system' projects.
The administrator can, following the usual project logic, alter quota by
modifying the project. Users cannot apply for modification of their system
projects.

Projects will, from now on, be identified by a UUID. System projects will
receive the same UUID as the user itself. ProjectID, which appears above in
the Quotaholder entries, refers to the project UUID. In order to ensure that
UUIDs remain unique across users and projects, we will first create the
system project and then copy its UUID to the new user (in a single
transaction).

Base quota will be expressed both in terms of a project-level and a
member-level limit. This will result in two operationally equivalent
Quotaholder counters, as in the following example. In the future, we could
admit third-party users to a user's system project; in that case, those
counters would differ.

::

  resource      holder         source         limit   usage
  ------------|--------------|--------------|-------|------
  cyclades.vm   project:uuid   None           5       1
  cyclades.vm   user:uuid      project:uuid   5       1

Private projects
----------------

Since the introduction of system projects will explode the number of total
projects, we will need to control their visibility. We add a new flag
*private* in project definitions. A private project can only be accessed by
its owner and members and not be advertized in the UI. System projects are
marked as private.

Decouple projects from applications
-----------------------------------

System projects do not fit well in the current project/application scheme,
because no user has applied for them. Moveover, we would like to easily
modify project properties, particularly quota limits, without the need to
apply for an application for each project and then approve it.

We will decouple projects from applications by incorporating the project
definition into the project object rather than relying on an application.
The system will directly make a new (system) project upon user creation and a
privileged user will be able to modify an existing project by directly
modifying it. An unprivileged user will still need to make an application.

The project model is adapted to reference the *last* application that is
related to the project, if any---projects automatically created by the
system reference no application. For an uninitialized project, this
denotes the original application through which the project was made. If
the application is denied or cancelled, the whole project is considered
deleted.

Applications as modifications
`````````````````````````````

Application for a new project is created in state ``pending`` and its
properties are copied into a new project object, which is in state
``uninitialized``. To preserve this equality, we disallow modifications of
uninitialized projects, either in-place or through an application. An
already activated project can be modified by submitting an application
containing just the desired changes. An application object stores the
specified changes and should remain read-only.

System default quota and resource registration
----------------------------------------------

Each resource registered in the system is assigned a default quota limit.
A newly-activated user is given these limits as their base quota. This is
till now done by copying the default limits as user's entries in
AstakosUserQuota. Default limits will from now on be copied into the system
project's resource definitions.

Conventional projects are created through a project application, which
may not specify limits for all resources registered in the system. In
fact, it may even be impossible to specify a resource, if it is set
``api_visible=False``. We have to somehow specify these limits. Defaulting
to zero is not appropriate: if we don't want to control a resource, we
would like it set to infinite. We thus need an extra skeleton, like the
one specifying the default base quota, in order to fill in missing limits
for conventional projects. It will be controled by a new option
``--project-default`` of command ``resource-modify``.

When a project is activated, either directly in the case of system projects
or through the approval of a project application, limits for resources not
specified are automatically completed by consulting the appropriate
skeleton.

Allocation of a new resource
----------------------------

When a service allocates a new resource, it should associate it both with a
user and a project. The commission issued to the Quotaholder should attempt
to update all related counters. For example, it should include the following
provisions::

  "provisions": [
          {
              "holder": "user:user-uuid",
              "source": "project:project-uuid",
              "resource": "cyclades.vm",
              "quantity": 1
          },
          {
              "holder": "project:project-uuid",
              "source": None,
              "resource": "cyclades.vm",
              "quantity": 1
          },
          {
              "holder": "user:user-uuid",
              "source": "project:project-uuid",
              "resource": "cyclades.cpu",
              "quantity": 2
          },
          {
              "holder": "project:project-uuid",
              "source": None,
              "resource": "cyclades.cpu",
              "quantity": 2
          }
  ]

If any of these provisions fails, i.e. either on the project-level limits or
the user-level ones, the whole commission fails.

The astakosclient call ``issue_one_commission`` will be adapted to abstract
away the need to write both the user-level and the project-level provisions.
The previous commission will be issued with::

  issue_one_commission(holder="user-uuid", source="project-uuid",
                       provisions={"cyclades.vm": 1, "cyclades.cpu": 2})

The service is responsible to record this resource-to-project association.
In Cyclades, each VM, floating IP, or other distinct resource should be
linked to a project. Pithos should link containers to projects.

Astakos will handle its own resource ``astakos.pending_app`` in a special
way: it will always be charged at the user's system project.

Resource reassignment
---------------------

The system will support reassigning a resource to a new project. One needs
to specify all related resource values. Astakosclient will provide a
convenience function ``issue_resource_reassignment`` to construct all needed
provisions. For instance, reassigning a VM with two CPUs can be done with::

  issue_resource_reassignment(holder="user-uuid",
                              from_source="from-uuid", to_source="to-uuid",
                              provisions={"cyclades.vm": 1, "cyclades.cpu": 2})

This will issue the following provisions to the Quotaholder::

  "provisions": [
          {
              "holder": "user:user-uuid",
              "source": "project:from-uuid",
              "resource": "cyclades.vm",
              "quantity": -1
          },
          {
              "holder": "project:from-uuid",
              "source": None,
              "resource": "cyclades.vm",
              "quantity": -1
          },
          {
              "holder": "user:user-uuid",
              "source": "project:from-uuid",
              "resource": "cyclades.cpu",
              "quantity": -2
          },
          {
              "holder": "project:from-uuid",
              "source": None,
              "resource": "cyclades.cpu",
              "quantity": -2
          },
          {
              "holder": "user:user-uuid",
              "source": "project:to-uuid",
              "resource": "cyclades.vm",
              "quantity": 1
          },
          {
              "holder": "project:to-uuid",
              "source": None,
              "resource": "cyclades.vm",
              "quantity": 1
          }
          {
              "holder": "user:user-uuid",
              "source": "project:to-uuid",
              "resource": "cyclades.cpu",
              "quantity": 2
          },
          {
              "holder": "project:to-uuid",
              "source": None,
              "resource": "cyclades.cpu",
              "quantity": 2
          }
  ]

API changes
-----------

API call ``GET /quotas`` is extended to incorporate project-level quota. The
response contains entries for all projects for which a user/project pair
exists in the quotaholder::

  {
      "project1-uuid": {
          "cyclades.ram": {
              "usage": 2147483648,
              "limit": 2147483648,
              "pending": 0,
              "project_usage": ...,
              "project_limit": ...,
              "project_pending": ...
          },
          "cyclades.vm": {
              ...
          }
      }
      "project2-uuid": {
          ...
      }
  }

An extra or differentiated call may be needed to retrieve the project quota
regardless of user::

  GET /quotas?mode=projects

  {
      "project-uuid": {
          "cyclades.ram": {
              "project_usage": 2147483648,
              "project_limit": 2147483648,
              "project_pending": 0
          }
          "cyclades.vm": {
              ...
          }
      }
  }

``GET /service_project_quotas`` will be used in a similar way as ``GET
/service_quotas`` to get the project-level quotas for resources associated
with the Synnefo component that makes the request.

All service API calls that create resources can specify the project where
they will be attributed.

In cyclades, ``POST /servers`` (likewise for networks and floating IPs) will
receive an extra argument ``project``. If it is missing, the user's system
project will be assumed. In calls detailing a resource (e.g., ``GET
/servers/<server_id>``), the field ``tenant_id`` will contain the
project id.

Moreover, extra calls will be needed for resource reassignment,
e.g::

  POST /servers/<server-id>/action

  {
      "reassign": {"project": <project-id>}
  }

In pithos, ``PUT`` and ``POST`` calls at the container level will accept an
extra optional policy ``project``. The former call assigns a newly created
container to a given project, the latter reassigns an existing container.
Field ``x-container-policy-project`` will be retrieved by a ``HEAD`` call at
the container level.

Changes in the projects API
```````````````````````````

``PUT /projects/<proj_id>`` will be used to mod a new project replacing
``POST``. It now expects a dictionary with just the desired
changes, not a complete project definition. It is only allowed if the
project is already activated.

``GET /projects/<proj_id>`` changes to include a ``last_application`` field,
if applicable.

Application actions (approve, deny, dismiss, cancel) are integrated into
project actions and expect an extra ``app_id`` argument to specify the
application. Actions are allowed only on a project's last application;
the application id is required in order to avoid races.

The applications API is removed, incorporated into the projects API.

User interface
--------------

User quota will be presented per project, including the aggregate activity
of other project members: the Resource Usage page will include a drop-down
menu with all relevant projects. By default, user's system project will
be assumed. When choosing a project, usage for all resources will be
presented for the given project in the following style::

                        limit
    used                ^                    taken by others
  |::::::|..............|...........|::::::::::::::::::::::::::::::::::|
         ^              ^                                              ^
         usage          effective                                      project
                        limit                                          limit


                        limit
    used                ^          taken by others
  |::::::|........|:::::|::::::::::::::::::::::::::::::::::::::::::::::|
         ^        ^                                                    ^
         usage    effective                                            project
                  limit                                                limit

Text accompanying the bar could mention usage based on the effective limit,
e.g.: `usage` out of `effective limit` Virtual Machines. Likewise the shaded
`used` part of the bar could express the same ratio in percentage terms.

Given the above-mentioned response of the ``/quotas`` call, the effective
limit can be computed by::

  taken_by_others = project_usage - usage
  effective_limit = min(limit, project_limit - taken_by_others)

Projects show up in a number of service-specific user interactions, too.
When creating a Cyclades VM, the flavor-choosing window should first ask
for the project where the VM will be charged before showing the
available resource combinations. Likewise, creating a new container in
Pithos will prompt for picking a project to associate with.

Resource presentation (e.g. Cyclades VMs) will also mention the associated
project and provide an action to reassign the resource to a different
project.

Command-line interface
----------------------

Quota can be queried per user or project::

  # snf-manage user-show <id> --quota

  project  resource    limit  effective_limit usage
  -------------------------------------------------
  uuid     cyclades.vm 10     9               5

  # snf-manage project-show <id> --quota

  resource    limit  usage
  ------------------------
  cyclades.vm 100    50

A new command ``snf-manage project-modify`` will enable in-place
modification of project properties, such as their quota limits.

Currently, the administrator can change the user base quota with:
``snf-manage user-modify <id> --base-quota <resource> <capacity>``.
This will be removed in favor of the ``project-modify`` command, so that all
quota are handled in a uniform way. Similar to ``user-modify --all``,
``project-modify`` will get options ``--all-system-projects`` to
allow updating base quota in bulk.

Migration steps
===============

Project conversion
------------------

Existing projects need to be converted to resource-pool ones. The following
steps must be taken in Astakos:
  * compute project-level limits for each resource as
    max_members * member-level limit
  * create system projects based on base quota for each user
  * make Quotaholder entries for projects and user/project pairs
  * assign all current usage to the system projects (both project
    and user/project entries)
  * set usage for all other entries to zero

Cyclades and Pithos should initialize their project attribute on each resource
with the user's system project, that is, the same UUID as the resource owner.

Initial resource reassignment
-----------------------------

Once migration has finished, users will be off-quota on their system project,
if they had used additional quota from projects. To alleviate this
situation, each service can attempt to reassign resources to other projects,
following this strategy:
  * consult Astakos for projects and quota for a given user
  * select resources that can fit in another project
  * issue a commission to decrease usage of the system project and likewise
    increase usage of the available project
  * record the new ProjectUUID for the reassigned resources
