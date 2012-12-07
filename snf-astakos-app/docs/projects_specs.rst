Synnefo Projects
================

Projects can be thought of as contracts between the infrastructure
and the members of the project, so that resources can be allocated
by the members and used for a specified period in time.

Definition
----------
A **definition** for a project represents the initialization
or modification of a project has the following attributes:

``name``
    *in dot-hierarchical dns-like form*

``description``
    *text describing the project for the public*

``start_date``
    *when the project is to be started*

``end_date``
    *when the project is to be ended*

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

``limit_on_members_number``
    *the maximum number of members that can be admitted to the project*

``limits_on_resources``
    *a set of limits on the total resources the group can grant to its members*

``resource_grants``
    *a set of resource usage limits each member is granted by the project*



Application for a Project
-------------------------
An **application** for a project must be issued by a user and
approved by the Service before any resources are granted.
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



Project Membership
-------------------------
A *project membership* object maps a user to a project and holds
state for this mapping.
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

The transitions from 2b to 3, and 5 to 6, must first
commit their starting state and then only update to the next state
after the *Synchronize Membership* procedure has been
acknowledged as successful.

Except states 2b and 5 which explicitly state that they are *pending*,
all other states are considered *synchronized*



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
    *the application which has created or modified the project.
    An application is approved by setting it to this attribute.*

``last_application_synced``
    *the last application that was successfully synchronized with Quotaholder.
    Normally, this is the same as the ``application`` above.
    However, on approval, only ``application`` is set
    so the two attributes differ, marking the project as pending definition
    synchronization. Upon successful synchronization with Quotaholder,
    ``last_application_synced`` is also set,
    marking the project definition synchronized.
    Note that if during the synchronization another approval
    updates ``application``, then after synchronization the project
    is still out of sync, and needs another loop.*

``creation_date``
    *when the project was created (i.e. was first approved)*

``last_approval_date``
    *when was the last approval (i.e. creation or modification).
    Null if the project has not been approved or has been suspended.*

``termination_start_date``
    *when the project was ordered to terminate,
    and declared out of sync for its resource grants to be removed.
    (is null if the project has not been ordered to terminate)*

``termination_date``
    *when the project termination was actually completed by the service
    following the successful revocation of resource grants.
    (is null if the project has not been terminated)*

``members``
    *the set of members for this project*

``membership_dirty``
    *boolean attribute declaring that the project
    needs membership synchronization.
    It must be atomically set and committed before
    any synchronization begins.
    It must be unset only after synchronization
    has been confirmed as successful.*



Rules
-----

1. **Valid projects**

    Projects are valid only if they violate none of the rules

2. **Active projects**

    A project is declared **active** when its resource grants are in effect.
    A valid project can be active if and only if
    - its ``last_approval_date`` is not null
    - its ``termination_date`` is null
    - its ``limit_on_members_number`` and ``limits_on_resources`` are not violated

2. **Terminated projects**

    A valid project is declared **terminated**, if and only if
    its ``termination_date`` is not null

4. **Suspended projects**

    A valid project is declared **terminated** if and only if
    
    - its ``termination_date`` is null
    - its ``last_approval_date`` is null,
      or its ``limit_on_members_number`` and ``limits_on_resources`` are violated

5. **Alive projects**

    Projects are declared **alive** if they are either *active*, or *suspended*.
    Users and owners are always able to interact with alive projects.

6. **Life status**

    The status of being alive, active, suspended, terminated.

7. **Project states**

    The states of a project that are significant from a control flow aspect,
    are the following:

    :(0):   pending approval
    :(1a):  alive, pending definition sync
    :(1b):  alive, pending membership sync
    :(1c):  alive, pending total sync
    :(2):   alive
    :(3a):  terminated, pending definition sync
    :(3b):  terminated, pending membership sync
    :(3c):  terminated, pending total sync
    :(4):   terminated


7. **Synchronization status**

    The status of the project's synchronization with Quotaholder
    can be either **synchronized** or **unsyncrhonized**.

    An alive project is delcared synchronized by setting
    ``last_application_synced`` to be equal to the ``application``,
    and setting ``membership_dirty`` to false,

    Semantically, the project becomes synchronized when its application
    definition has been fully implemented and committed to quotaholder,
    and all its memberships are also synchronized.

    The alive project loses its synchronization on two occasions.
    On the approval of a new application modifying the project,
    and on the addition or removal of any of its memberships.

    In general, also considering projects under termination,
    a project is declared synchronized if and only if:

    - ``last_application_synced`` equals ``application``
    - ``membership_dirty`` is false
    - ``termination_start_date`` is null or ``termination_date`` is set

    Depending on which of the previous three clauses fail,
    a synchronizing process knows what to do:
    definition, membership, or termination and combinations.

8. **Unique project names**

    The project name (as specified in its application's definition)
    must be unique among all *alive* projects.

9. **Inconsistent dates**

    If either ``creation_date`` or ``last_approval_date``
    is in the future, the project state is declared **inconsistent**
    but the project is still considered created or approved, respectively.
    
    If ``termination_date`` is in the future, the project state is declared
    **inconsistent** but the project is still considered terminated.

10. **No project without application**

    A project can only exist in reference of the application that has defined it.
    The attributes in the definition such as its name, resource grants
    cannot be modified without a new application that must be approved.

11. **Creating and modifying projects with follow-up applications**

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
    (i.e. no project references it as its defining ``application``),
    then a new project entry is created and initialized.
    
    If the precursor of an application *is* associated with a valid project,
    then the same project entry is used and is re-initialized according
    to the new application's definition.
    The project is made alive (if terminated) and its previous state
    is maintained (mainly, the member set).
    If the new definition causes the project to exceed its limits,
    it will be suspended as required.



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

   A project is suspended by setting ``last_approval_date`` to None

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
and its appearance and function is accordingly parametrized.

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

