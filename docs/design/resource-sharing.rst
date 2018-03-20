Resource sharing
^^^^^^^^^^^^^^^^

This document describes the current state and proposed changes regarding
resource sharing in Cyclades.

Current state
=============

Cyclades supports four first-class resource types: *VirtualMachine*,
*Network*, *IPAddress*, *Volume*. Each such resource contains the following
attributes:

* ``userid``: UUID of the resource owner
* ``project``: UUID of the project
* ``shared_to_project``: True if resource is shared among project members

.. note:: ``project`` corresponds to OpenStack's ``project_id`` attribute.
          In Openstack, only VirtualMachines and Volumes also include a
          ``user_id`` attribute. (Networks and IPs just belong to the
          project).

Who does the resource belong to? It belongs to its owner, who has been
granted the right to own the resource through the project.

The owner is normally a member of the project. If they are removed from
the project, they lose the right to own the resource, and the cloud operator
can eventually reclaim it (destroy it). If the owner has free quota in some
other project, they can *reassign* the resource to that project in order to
keep it alive. In essence, projects are pools of *quota* rather than actual
resources.

Moreover, there exist resource types *Subnet* and *NetworkInterface*, that
contain only the attribute ``userid`` and are not quotable. Note that in
Openstack these resources include a ``project_id`` rather than a
``user_id``.

.. note:: Code-wise it is enforced that Subnet's ``userid`` equal the
          Network's ``userid``. A NetworkInterface can be created by anyone
          having access to the Network and the VirtualMachine.


Sharing
-------

When the ``shared_to_project`` flag is set, then any project member can
access and modify the resource up to destroying it. The only exceptions are
reassignment and unsharing, which remain the privilege of the resource
owner.

When an action involves multiple resources, things get more complicated.
Depending on the action, a user must have access to either both related
resources or just one of them.

For example, volume attachment actions (attach, detach) require access to
both the vm and the volume.

However, this is buggy when combined with unsharing or reassign actions.
Consider the following steps:

* User A shares their vm to the project
* User B attaches their own volume to the vm
* User A *unshares* the vm

After these steps, user A has effectively stolen the volume from user B (who
now cannot detach it). What's more, if user A now *reassigns* the vm to
another project and shares it there, then B's volume leaks to members of the
new project.


Addressing issues
=================

We need to restrict the interaction of sharing, and relating resources.
In particular, a project resource must not leak to another resource. An
admin must never lose access to their resource.

Multitenancy solution
---------------------

If we want to move to the direction of multitenancy, we must assume that it
is the *project* who actually owns the resource. The project delegates the
administation of the resource to one of its users, the resource *admin*.
Finally, any project member, a *user* can access the resource, provided that
it is shared to project members.

In this context, it doesn't make sense to relate resources of different
projects; therefore, all actions must preserve the:

  **Invariant 1:** Related resources must belong to the *same project*.

Assume the user attributes:

* *resource_admin*: request user is the admin of the (main) resource
* *attachment_admin*: request user is the admin of the attachment in an
  action that involves a main resource and an attachment
* *resource_user*: request user is the resource admin or has access through
  sharing
* *attachment_user*: request user is the attachment admin or has access
  through sharing

the resource status attributes:

* *shared_resource*: resource is shared to the project
* *shared_attachment*: attachment is shared to the project
* *pure_resource*: resource is not related to resources of other admins
* *pure_attachment*: attachment is not related to resources of other admins
* *same_project*: main resource and attachment belong to the same project

as well as the usual boolean operators.

The following table describes when the conditions that must hold for an
action to apply.

.. csv-table:: Rules table 1
   :header: "Resource", "Action", "Actor", "Status", "Comment"
   :widths: 15, 10, 25, 25, 40

   "any", "reassign", "resource_admin", "!shared_resource & pure_resource", "changes all
   related resources in a block"
   "any", "share",    "resource_admin", "any"
   "any", "unshare",  "resource_admin", "any"

   "vm", "start",    "resource_user",  "any"
   "vm", "destroy",  "resource_user",  "any"

   "volume_attachment", "create", "resource_user&attachment_user", "same_project"
   "volume_attachment", "destroy", "resource_user|attachment_user", "any"

Relaxing the restriction
------------------------

If we want to accommodate the current practice of relating resources that a
single user has acquired from different projects, we can relax the
invariant as follows:

  **Invariant 2:** Related resources of a *non-pure* or *shared* resource
  must belong to the *same project* as the resource itself.

The rules now are changed as follows.

.. csv-table:: Rules table 2
   :header: "Resource", "Action", "Actor", "Status", "Comment"
   :widths: 15, 10, 25, 25, 40

   "any", "reassign", "resource_admin", "!shared_resource & pure_resource", "applies to the
   specified resource only"
   "any", "share",    "resource_admin", "same_project"
   "any", "unshare",  "resource_admin", "any"

   "vm", "start",    "resource_user",  "any"
   "vm", "destroy",  "resource_user",  "any"

   "volume_attachment", "create", "resource_admin & attachment_admin", "!shared_resource & !shared_attachment"
   "volume_attachment", "create", "resource_user & attachment_user", "(shared_resource | shared_attachment) & same_project"
   "volume_attachment", "destroy", "resource_user | attachment_user", "any"

Note that in this case, user A of the example can still unshare the vm,
however, not leak it to another project. User B has still access to their
volume and can detach it. Similarly, a user who owns a volume from project P
can attach it to their vm from project Q, but then cannot share either of
them.
