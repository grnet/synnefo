Synnefo Projects: General Design Notes
======================================

Projects can be thought of as "contracts" between the infrastructure
and the members of the Project, so that members can allocate and use
resources for a specified period in time.
For every Project there is an *application*, and a *membership set*.
The application must be approved before the Project "contract"
comes in effect, and before any members join.

Applications contain a Project *definition* that formally includes
all the policy of the Project "contract", such as name, ownership,
dates, and resource limits.
Applications and the definitions they contain are, like contracts,
immutable objects that can be tracked and effected in their entirety.
Every change made to a pending application or an existing Project
must be applied for through a new application.

Project Synchronization
-----------------------
A Project has two kinds of effects, global and per-membership.
Global effects are encoded within the Project object itself,
and may include services (e.g. dns name, website, forum/collaboration),
project-wide resources (e.g. VMs, IPs, diskspace), etc.
Per-membership effects are encoded within Membership objects,
and are prescribed by the policy in the project definition.

By design, the effects of the project are expected to extend
beyond the database system that records the project approval,
therefore these effects cannot be relied to be implemented
instantly and atomically upon request.
For example, project creation or modification may involve
updating resource management services, notification services,
project website services, which may all have their own separate
database systems.

Consequently, once a policy is (atomically) registered as being in effect,
it must be propagated for implementation with separate (non-atomic) procedures,
collectively called Project Synchronization.

Currently, the general approach for Synchronization of synnefo Projects,
is to maintain appropriate states for the objects encoding policy effects
(i.e. Project and Membership objects), and execute careful transitions
among those states, respecting semanting dependencies and limitations,
and remote system accesses.
For example, a project cannot be considered "synchronized" unless
all its Memberships are also considered "synchronized",
or you cannot declare a Membership as synchronized if the newly-set
quotas have not been acknowledged by the remote quota service.

Creating and Modifying Projects
-------------------------------
Projects are created and modified by issuing a corresponding application.
Applications that refer to the same Project are chained by including
a reference to the precursor application into the new one.
Applications that do not specify a precursor always create a new Project
(that is, a new project object with a new membership set).
Project applications that have not yet been approved may also be modified.
When an unapproved application is modified (ie. it is succeeded by another),
it may or may not be automatically rejected, depending on policy.

Projects once created, are expected to always remain in record,
even if they have been deactivated (i.e. their policies removed from effect).
Deactivating a project may be the result of a policy-specific action,
such as *termination* on a pre-defined date or *suspension* following
an administrative decision.
Deactivated projects retain both their Definition and their Membership sets,
allowing them to be reactivated by another kind of policy-specific action.

Adding and Removing Project Members
-----------------------------------
Memberships once created, are also expected to remain in historical record,
even if they have been marked as removed by a policy-specific action,
such as the user leaving the project,
or the project owner suspending, or terminating them altogether.



Reference Schema for Projects
=============================

General Terms
-------------
For clarity and precision, we (try to) use different terms for similar meanings.
We also separate low-level technical primitives from related higher-level
policy actions that include them.

synchronize, synchronized, synchronization
    A low-level term for Projects and Memberships.
    Refers to the controlled (non-atomic) process that implements
    a newly modified policy (i.e. adds or removes policy effects
    such as quota limits).

activate, deactivate, active, inactive
    A low-level term for Projects and Memberships.
    A Project or Membership is considered active as long as
    its policy is in effect.

suspend, suspended, suspension
    A policy term for Projects and Memberships,
    implying temporary deactivation by an administrative action
    (e.g. abuse report, limits violation).

terminate, terminated, termination
    A policyu term for Projects and Memberships,
    implying permanent deactivation, especially
    according to a pre-defined end-of-life event
    (e.g. project/contract "expiration").

add or remove membership
    Low-level terms for managing memberships to projects.

join or leave project
    Policy terms for when users request their addition or removal
    from a project membership set.

accept or reject membership request
    Policy terms for a project administrator to decide on
    join or leave requests.

approve or disapprove project
    Policy terms for service administrators to decide whether
    to create/activate a project according or not

alter project
    Low-level term for changes made to the global (i.e. not Membership)
    project status (e.g. new application, suspension).

modify project
    Policy term for submitting a new application as a successor
    to an existing one, to alter the definition of a project.

project leader
    The user who has authority over a project,
    to accept or reject membership requests,
    or to perform other actions according to policy.

project applicant
    The user who submits a project application for creation
    or modification of a project.
    The applicant can be a different user than the leader.

project administrator
    A user who has authority to approve, disapprove, and modify
    projects of a certain class (e.g. according to their domain names).


Definition
----------
A **definition** for a project, which represents the initialization
or modification of a project, has the following attributes:

``name``
    *in dot-hierarchical dns-like form*

``description``
    *text describing the project for the public*

``start_date``
    *when the project is requested to become active*

``end_date``
    *when the project is to be deactivatedended*

``member_join_policy``
    *an enumeration of policies on how new join requests are to be accepted.
    The policies include the following:*

    ``auto_accept``
        *new join requests are automatically accepted by the system*

    ``owner_accepts``
        *new join requests must be accepted by the owner of the project*

    ``closed``
        *no new members can join the project, even if old ones leave*

``member_leave_policy``
    *an enumeration of policies on how new leave requests are to be accepted.
    The policies include the following:*

    ``auto_accept``
        *leave requests are automatically accepted by the system*

    ``owner_accepts``
        *leave requests must be accepted by the owner of the project**

    ``closed``
        *no member can leave the project*

``limit_on_member_count``
    *the maximum number of members that can be admitted to the project*

``limits_on_resources``
    *a set of limits on the total resources the group can grant to its members*

``resource_grants``
    *a set of resource usage limits each member is granted by the project*



Application for a Project
-------------------------
An **application** for a project must be issued by a user and
*approved* by the service before any resources are granted.
Its attributes are:

``serial``
    *a unique serial number identifying the application*

``applicant``
    *who applies for creation or modification of a project*

``owner``
    *the requested owner of the project*

``comments``
    *text comments for the application*

``definition``
    *the definition of the project being requested*

``issue_date``
    *when the application was submitted*

``precursor_application``
    *a reference by serial to a previous application which this application
    requests to modify. It can be null if there is no precursor.*

An application is immutable in its attributes above,
but its status depends on how it has been processed.
The *application status* can be:

    :(1):   pending
    :(2a):  approved
    :(2b):  rejected
    :(3):   replaced

When an application becomes *approved* and therefore defines
a the project, its precursor (if any) must atomically be set to *replaced*.



Project Membership
-------------------------
A *project membership* maps a user to a project and holds state for this mapping.
There are no inherent constraints to this mapping,
any user might be a member to any project.

The **state** of membership can be:

    :(1):   *pending acceptance*
    :(2a):  *rejected*
    :(2b):  *accepted, pending synchronization*
    :(3):   *active*
    :(4):   *pending removal*
    :(5):   *removed, pending synchronization*
    :(6):   *removed*

The transitions from 2b to 3, and 5 to 6, must first commit
their starting state and then only update to the next state
after the *Synchronize Membership* procedure has been
acknowledged as successful.

Except states 2b and 5, which explicitly state that they are
*pending synchronization*, all other states are considered *synchronized*
**Synchronization** refers to all external communication 
(i.e. not within the limits to) required



Project
-------
A **project** is created or modified upon the approval of an application.
It is initialized with the *definition* contained in the application,
and grants resources as specified, and acquires all the extra state needed.
The *definition* of a project does not belong to its mutable state,
and can only be changed by approving a new application.
The attributes for a project are:

``serial``
    *a unique serial number identifying the project*

``application``
    *the last application that was successfully synchronized with Quotaholder.*

``creation_date``
    *when the project was created (i.e. was first approved)*

``last_approval_date``
    *when was the last approval (i.e. creation or modification).
    Null if the project has not been approved or has been suspended.*

``deactivation_start_date``
    *when the project was ordered to deactivate,
    and declared out of sync for its resource grants to be removed.
    (is null if the project has not been ordered to deactivate)*

``deactivation_date``
    *when the project deactivation was actually registered as completed
    by the service following the successful revocation of resource grants.
    (is null if the project has not been deactivated)*

``deactivation_reason``
    *Text indicating indicating the reason for deactivation.*

``members``
    *the set of memberships for this project*


Rules
-----

1. **Valid projects**

    Projects are valid only if they violate none of the rules

2. **Active projects**

    A project is declared **active** when its resource grants and
    general policy is in effect (even if partially),
    and no order of deactivation has been given.

    A valid project can be active if and only if
    - its ``deactivation_start_date`` is null

2. **Inactive projects**

    A valid project is declared **inactive** when its resource grants
    and general policy is not in effect, or is in effect and

    A valid project is inactive if and only if,
    its ``deactivation_start_date`` is not null

3. **Project states**

    The states of a project that are significant from a control flow aspect,
    are the following:

    :(0):   pending approval
    :(1a):  active, pending definition sync
    :(1b):  active, pending membership sync
    :(1c):  active, pending total sync
    :(2):   active
    :(3a):  inactive, pending definition sync
    :(3b):  inactive, pending membership sync
    :(3c):  inactive, pending total sync
    :(4):   inactive


4. **Synchronization status**

    The status of the project's synchronization with Quotaholder
    and other remote services,
    can be either **synchronized** or **unsyncrhonized**.

    Semantically, the project becomes synchronized when its application
    definition has been fully implemented and committed to quotaholder,
    and all its memberships are also synchronized.

    The active project loses its synchronization on two occasions.
    On the approval of a new application modifying the project,
    and on the addition or removal of any of its memberships.

    In general, also considering projects being deactivated,
    a project is declared synchronized if and only if:

    - None of its Memberships is unsynchronized
    - ``deactivation_start_date`` is null or ``deactivation_date`` is set

5. **Unique project names**

    The project name (as specified in its application's definition)
    must be unique among all *alive* projects.

6. **Inconsistent dates**

    If either ``creation_date`` or ``last_approval_date``
    is in the future, the project state is declared **inconsistent**
    but the project is still considered created or approved, respectively.

    If ``deactivation_date`` is in the future, the project is declared
    **inconsistent** but the project is still considered inactive.

7. **No project without application**

    A project can only exist in reference of the application that has defined it.
    The attributes in the definition such as its name, resource grants
    cannot be modified without a new application that must be approved.

8. **Creating and modifying projects with follow-up applications**

    Every application for a project can be followed up with another one.
    The new application points back to it with its ``precursor`` attribute.

    This means that an applicant can update their application
    before it has been approved.

    Apart from an applicant, whoever can approve the project,
    can also post a follow up application for it, modifying
    some aspects of the definition and approve that instead.
    For example, a user might request for 100 GB storage,
    but the Service may approve a project with only 80GB,
    via a follow up application.

    If the precursor of an application is not associated with a project
    (i.e. no project references it as its defining ``last_application_approved``),
    then a new project entry is created and initialized.

    If the precursor of an application *is* associated with a valid project,
    then the same project entry is used and is re-initialized according
    to the new application's definition.
    The project is made active (if inactive) and its previous state
    is preserved (mainly, the member set).


Scenarios
---------

Project applicant not confident for his numbers
'''''''''''''''''''''''''''''''''''''''''''''''
Researcher requests resources to create a cluster for a protein-folding
computation experiment. He knows how exactly how many machines,
memory, and disk he needs but is not certain how many CPU cores
he should request.

He leaves the corresponding resource unspecified,
and leaves a comment noting the issue.

The project administrator responsible for the application
uses his expertise, and/or consults others to formulate an appropriate
limit for the resource.
Then he modifies the (not-yet-approved) project, fills in the resource limit,
then submits and approves the new application.


Using participation to support an project application
'''''''''''''''''''''''''''''''''''''''''''''''''''''
An applicant knows that his application will be rejected unless
a lot of people support it.

Therefore, he applies for a project with no resource grants,
and notes his rationale in the comments.

The project administrator accepts his application in good faith,
and then the project begins to accept members.

Once many and important enough members have joined,
the project leader modifies the project with a new application
that now includes significant resource grants.

The project administrator reviews the application and membership list,
and is convinced that the project deserves the grants.
However, he wants to make sure that this remains so,
by ensuring that the membership of the project cannot
include other users without further review.

Therefore, he further modifies the (not-yet-approved) application,
and sets the member accept policy to be 'closed', that is,
that no new members may join the project.
Then he sumbits and approves the application.



-------- gtsouk REVIEW STOPS HERE ---------

Procedures
----------

The following procedures are considered essential primitives
for the function of the Projects feature, and should constitute
a natural *internal* API to it. This is not a public API for users,
although the public one should be thinly layered on top of it.

For quotaholder interactions, a primitive to synchronize quotaholder
with a user's resource quotas is assumed to be available.

#. Submit an application

   Every user might submit an application to create or modify a project.
   There are no inherent constraints.
   However, policy may impose restrictions.

#. Retrieve applications

   Applications should be retrievable by serial, by applicant,
   and by approval status.
   Because applications are immutable, some kind of extra state
   is needed in order to index by approval status.
   For example, one might instantiate a mutable object for approval state,
   with attributes (``approval_serial``, ``approval_state``, ``approval_data``)

#. Approve an application (create or modify a Project)

   Application approval must atomically perform and commit all of the following:
   - create or modify the project at its specified definition
   - set the project state to be pending synchronization with quotaholder

   After committing, the procedure to synchronize the project (see below)
   should be called.

#. Retrieve projects

   Projects should be retrievable by serial, by owner,
   by application, by life status, and by synchronization status.

   *By application* means that given an application, one must be able
   to retrieve the project that has it approved, if any.

#. Add or remove a user to a project

   When a new membership is created for a project or
   an existing one is modified, then in the same
   transaction the project must be declared *unsynchronized*.

#. Suspend a project

   A project is suspended by setting ``last_approval_date`` to None.

#. Terminate a project

   Project termination must atomically perform and commit all of the following:
   - set the project ``termination_start_date``
   - set the ``termination_date`` to null (this is a redundant safeguard)
   in order to mark the project as pending termination synchronization.

   After committing, the procedure to synchronize the project (see below)
   should be called.

#. Synchronize a membership with quotaholder

   This procedure is not required to be an independent procedure
   available for individual memberships.
   That is, if user synchronization takes care of all memberships,
   one can call user synchronization instead of membership synchronization.

#. Synchronize a user with quotaholder

   User synchronization is equivalent to the synchronization of
   all the user's memberships.

#. Synchronize a project with quotaholder

   Project synchronization is equivelent to the synchronization of
   either all its memberships, or all its members.



View elements
-------------
In this context, view elements refer to (at best effort) self-contained
elements that display information for and offer interaction with their
underlying objects. A final view, such as a web page, or console command
output, may include several elements.

Interaction with the feature is going through several view elements.
Each element has two pieces of input,
the *objects being referenced*, and the *accessing user*,
and its appearance and function is accordingly parameterized.

Each *project element* may need to display information
that internally belongs to its linked object,
such as its *definition* or *memberships*.

A proposed list of elements is following.
The elements are only considered building blocks
for views and not full views by themselves.
More on views later on.

#. Project list element

   This represents a list of *projects.*
   Technically, most of information about a project resides in its *application*.

   In the case of a *pending application*,
   one that has not been approved yet,
   then the row is filled with data from the
   current (approved and effective) application,
   or they are left blank if no such project exists yet.

   Additionally, the column that displays the pending status
   of the project (creation or modification), should be a link
   to the corresponding application detail element.

#. Membership element

   A list of project members for a single (or maybe multiple) projects.
   The list must not display user emails if the viewer is not the owner
   of the group, or a service administrator.

#. Application details element

   Displays all application details in full,
   with a link to the (alive) project it defines, if any,
   or a pending notice,
   or an obsolescence note if the project it defined was since modified,
   or a rejection notice.

#. Project details element

   This element contains both details for the defining application
   and for the current state of the project.

   Details for the current state of the project may include
   statistics on membership and resource usage.

#. Application form element

   It submits a new application.
   If the application is in reference
   to previous application (the ``precursor``)
   then the form should be initialized to be a copy of it.

   Otherwise, it may be blank, or initialized with defaults from a template.

#. Project search element

   This is an entry point to a listing, with configurable filtering.

#. History and statistics view

   No specification currently.

