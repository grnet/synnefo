Design document for VM instance tags
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This document presents the proposed design for the support of virtual machine
instance tags in Synnefo.  The notion of instance tags includes the various
types of parameters, such as, os, disk, and hypervisor, offered by Ganeti.


Motivation
==========

The need for instance tags is driven by the following use cases we would like to
serve:

- VMs with too much memory often need to be marked with the "always_failover"
  backend parameter 

- VMs that need smtp connectivity need to be marked with a tag that will disable
  the firewall

- There are parameters/tags that will need to be set in the future to support
  more QoS features


Current state and shortcomings
==============================

The following bullet points summarise the current state and highlight its
shortcomings.

- Parameters/tags are initialized in hard code at instance creation.

- Cyclades does not set any VM parameters/tags, although they are supported by
  RAPI.

- Cyclades does not keep nor manage any state of parameters/tags.

- There is no internal Cyclades API to configure parameters/tags of a VM that is
  being created.


Proposed changes
================

- Extend Cyclades's REST API to support VM instance tags according to
  `OpenStack's corresponding API <https://developer.openstack.org/api-ref/compute/#list-tags>`_.:

  - Specifically, the API will support:

    - specifying tags when creating a VM instance
    - listing the existing tags
    - replacing all existing tags with a new set
    - deleting all tags
    - checking whether a tag exists
    - adding a tag
    - deleting a tag

  - Extend Cyclades's database model to record a VM instance's tags

- Assign Cyclades REST API tags as Ganeti instance tags:

  - Use Ganeti's RAPI client to manage tags in existing create_instance
    operations, as well as in specialized tag managing operations.
  - To allow various components to have their own prefixes (e.g. separate REST
    API user-provided vs Cyclades logic-provided tags) use a different tag
    prefix per component.  Most importantly, this prevents end-users to access
    system-level tags.
  - Make tag-related jobs visible to eventd and dispatcher
  - Handle tag-related jobs that Ganeti failed
  - Reconcile Cyclades DB with the state held by Ganeti
  - Write functional tests for tag operations and execute them with snf-burnin

- Extend Kamaki to support management of VM instance tags

  - Extend the Kamaki clients to support VM instance tag operations
  - Extend the Kamaki cli with commands for VM instance tag management

- Extend snf-manage with commands for VM instance tag management


Implementation details
======================

To facilitate actions on groups of tags, Cyclades features a prefix-based
mechanism where tags contain a prefix that identifies the setter of the tag.  A
tag's prefix defines its namespace.  Cyclades will initially support two
prefixes:

- cyclades:user: for legitimate user(s) associated with the vm
- cyclades:system: for private use by cyclades components.

The naming convention for tags is:: <tag group>:<tag name>.

Openstack's Compute API specification for tags allows tag names to consist of
Unicode characters except for '/' and ','.  However, Ganeti only allows
alphanumeric characters plus the characters of the following set: '.+*/:-'.
To deal with this, a simple encoding/decoding scheme
(tag_to_ganeti()/tag_from_ganeti()) has been setup that reconciles the two
worlds by:

- encoding Unicode tags as UTF-8 strings
- using Python's quote_plus() to replace the non-ascii characters
- replacing '%' (the standard escape symbol) with '/' that is accepted by Ganeti
- replacing '_' (considered safe character by quote_plus and is not replaced)
  with '*' that is accepted by Ganeti.

The tag is stored in Cyclades DB in
clear text, but it is stored in encoded form at the Ganeti backend.  For tags
stored in Ganeti, the reverse transformations applied by tag_from_ganeti()
produce the user-provided UTF-8 encoded tag.

Two more limitations regard a tag's max length and the max number of tags per VM
instance.  Openstack sets the max length of tags to 60 characters, while Ganeti
allows up to 128.  Regarding the max number of tags per VM instance, OpenStack
allows 50, while Ganeti 4096.

According to the mentioned prefix scheme, normal users, even with admin
privileges, should not be able to manage system tags.
In general, tag setters are allowed to:

- specify tags when creating a VM instance; internally, an appropriate prefix
  will be provided to each tag that identifies the issuer
- list the existing tags they own; Cyclades will retrieve the tags and their
  status (ACTIVE or PENDADD) that start with the prefix corresponding to the
  issuer
- replace all existing tags they own with a new set; Cyclades will replace
  active tags with the corresponding prefix with a new set that is prefixed
  accordingly
- delete all tags they own; Cyclades will delete all active tags with the
  corresponding prefix
- check whether a tag they have set exists; Cyclades will search through tags
  with the corresponding prefix and return whether it exists and its status
- add a tag; internally the tag will be prefixed to identify its setter
- delete a tag they have set; Cyclades will delete the active tag with the
  corresponding prefix if one exists.

Tag prefixes are transparent to users.

The API calls regarding the listing of tags and checking whether a tag exists
include the tags' status.  This design provides OpenStack compatibility when it
comes to adding a new tag.  OpenStack states that response 201 is returned upon
a successful tag addition.  Unfortunately, to know that we would have to wait
for Ganeti to complete its async processing of a tag addition operation.
Instead we return 201 if everything has gone as planned, let aside the
processing of Ganeti, and attach status PENDADD to the newly created tags in
Cyclades DB.  Because list_tags and check_tag_exists return the tags' status,
users can tell whether the tags are active.

The meaning of an active tag regards its recorded state in the Cyclades
database.  The range of possible statuses is the following:

- PENDADD: pending to be added to the Ganeti backend (default)
- ACTIVE: successfully added both in Cyclades DB and the Ganeti backend

Only tags in ACTIVE state are modified, that is deleted or replaced.  Upon a
failed addition tags are deleted.  Upon a failed deletion tags remain active.
It is important to decide whether we will support parallel processing of tag
requests in order to address consistency concerns and agree on a consistency
model for this feature.

When an operation on tags is received from the REST API, the Cyclades API
handling routines append the user prefix to the specified tags or include the
prefix if an operation on all tags is requested, and pass these to the logic
layer.  The latter updates the Cyclades database, calls the corresponding
functions for running the jobs in the Ganeti backend, and returns to the API
layer (in this order).  The mechanism and logic of Cyclades tags is exposed in
logic/servers.py.  As a further step, before informing Ganeti about changes in
tags, the compatibility of new tags with existing ones will be checked. For
instance, a high-availability tag clashes with a high-performance tag. In this
case, if one of the two exists it will remain as is and the other will not be
applied. If both are to be added, then the call will abort with a bad request
response code.

The processing of a Ganeti job can go wrong.  In this case the snf-dispatcher
can help.  The snf-dispatcher processes the outcome of Ganeti jobs.
Specifically, it processes incoming notifications from AMQP queues that hold
Ganeti-related messages published by snf-ganeti-eventd.  Thus, if a job fails,
further action can be taken.  There are four different AMQP queues that concern
operations on a VM, network operations, the VM creation progress, and cluster
operations.  In order to implement safety measures for Ganeti jobs that execute
tag operations, we extended the handler function for the VM operations queue
(QUEUE_OP), that is update_db().  The tag operations submitted to Ganeti concern
the addition or deletion of tags.  At the time of submission, tags are persisted
in Cyclades DB with status PENDADD if they are to be added.  If they are to be
deleted, they are deleted from Cyclades DB first.  For better support of tag
operations, eventd has been modified to pass the set of tags handled by Ganeti.
Following a notification published by Ganeti on the outcome of a tag operation,
the snf-dispatcher updates the status of the corresponding tags in Cyclades DB
to ACTIVE for tag addition and deletes the tag(s) if the operation completed
successfully in Ganeti.  Then if tag deletion failed in Ganeti, the tag(s) are
reinstated in Cyclades DB.  This treatment serves also another use case; a
corner case of tag operations that regards the addition of tags manually through
GHaneti's API.  At the processing of the Ganeti job's notification by
snf-dispatcher (logic/backend.py: process_op_status()) it is checked whether the
new tags are prefixed accordingly. Then we check whether they exist in the
Cyclades backend. If not, they are created, encoded with
tag_to_ganeti(), and their status is set to 'ACTIVE'.  Finally, if tag addition
failed in Ganeti, tags are deleted from Cyclades DB.

Regarding reconciliation, it should happen according to a single point of truth.
Ganeti's state will be the baseline for the reconciliation process and the state
of the Cyclades's database will be updated accordingly to match Ganeti's.
Specifically, when a tag is present in Ganeti but it is not present in Cyclades
DB or it is present but not in active state, then the tag is created in Cyclades
DB if it includes a valid prefix.
If it already exists in Cyclades DB, then its state is updated to ACTIVE.
On the other hand, when a tag is present and in active state in Cyclades DB, but
is missing from Ganeti, then it is DELETED from Cyclades DB.

Considerations to discuss and address
=====================================

- Will we have quotas for tags?
- Will we process tag operations sequentially or will we allow parallel
  processing?  If tags are not quotable, will we allow parallel processing of
  requests for non-quotable resources and sequential for the quotable ones?
- What is the consistency model for this feature?
- Do we want to reconcile all tags or only a subset that is important to Ganeti?
- Should tag prefixes be settable or constants?

Future work
===========

- tags applicable at runtime?
