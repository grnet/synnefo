Atomic transactions with context
================================

Current state
-------------

1. Transaction decorators (commit_on_success) are placed at the API level
   (cyclades API, admin app, snf-manage commands), but there are also
   scattered ones at the logic level.

2. Some commit_on_success are nested, perhaps unintentionally.

3. There are explicit commits in code that handles Quotaholder serials.
   There is also ad hoc resolving of serials when an action fails.

Using atomic
------------

commit_on_success has been deprecated in favor of atomic. This is not a
drop-in replacement, primarily due to different semantics of nesting.
Moreover, explicit commits are not supported any more.

New design
----------

1. We move transaction decorators at the logic level. This way we can
   guarantee unified behavior across apps.

2. Transactions are encapsulated in a context handler; this is responsible
   to run deferred actions on transaction termination (commit or rollback).
   This will mostly be used to resolve quotaholder serials, but it can also
   be used to send ganeti commands or acknowledgment emails. To this end,
   we replace the @atomic decorator with our new @atomic_context decorator.
   This introduces a namesake kwarg on the decorated function, through which
   the body can have access to the context::

     @atomic_context
     def start(server_id, atomic_context=None):
       ....

   The caller can override the default handler by supplying its own
   atomic_context argument.

3. Code that issues commissions must always run in an atomic context and
   record the resulting serial on the context. Explicit commits and explicit
   resolving of serials are removed; we let the context handle them.

4. As a side-effect of moving transactions at the logic level, we must also
   move there the code that checks if an action is allowed. But this depends
   on the user credentials: An admin running through the admin app has
   higher permissions than a regular user who invokes the cyclades API.

   We add an extra argument 'credentials' in all logic functions. This is an
   object that contains any information is needed to check permissions, eg
   'userid', 'user_projects', 'is_admin'.

   For every resource type, we define a policy class which checks
   permissions for any kind of credentials. This will have a standard
   interface, covering all cases required, eg permissions for viewing a
   resource, for updating a resource, etc.

   As an example, consider the implementation of servers.start()::

    @transaction.atomic_context
    def start(server_id, credentials, atomic_context=None):
        with commands.ServerCommand(
                "START", server_id, credentials, atomic_context) as vm:
            log.info("Starting VM %s", vm)
            job_id = backend.startup_instance(vm)
            vm.record_job(job_id)
            return vm

   The ServerCommand manager is responsible to control access on the vm
   based on credentials.

5. Since credentials are now part of the logic, we can use it to improve
   action logging as well as to possibly vary the action behavior. For
   example, we can let an admin to start a VM even if the VM owner is
   overquota.
