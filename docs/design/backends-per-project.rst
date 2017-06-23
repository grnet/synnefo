Enable VM allocation to backends per project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This document describes the extension of Cyclades's backend allocator to
provision VMs on backends, taking into account project specific rules.


Current state and shortcomings
==============================
Currently Cyclades offers a simple mechanism to pin users to specific backends
with a dictionary configured in settings. This is fairly limited as it does
not allow reserving backends for specific users or allocating VMs belonging to
specific projects to certain backends. Furthermore it is a static configuration
which needs to be altered by a service administrator and to be replicated to
all Cyclades workers which in turn must all be restarted in order for any
change to take effect, causing service disruption.


Proposed changes
================
Cyclades need to be able to connect backends with certain projects. These
backends will be considered as possible backends that the VMs will be allocated
to. The same allocation procedure as befored will be followed (e.g., checking
if the VM fits or where it fits best) for choosing a specific backend.

This is a superset of the previous functionality, as each user has its own
personal project, so connecting the user's project with only one backend,
achieves the same functionality. The only difference with the previous
functionality is that if a user was pinned to a specific backend, no other
check was performed. Cyclades was issuing the allocation request to that
ganeti cluster without further allocation policy.

Furthermore, to allow reserving backends for specific users/projects we must be
able to declare a backend as being public/non-public. Public backends are
accessible by everybody and considered as possible backends for every
user/project. Non-public backends can be used only if a project is assigned to
one of these backends.

When re-assigning a VM, the reassignement must be prohibited if the target
project does not have access to the backend the VM was allocated to.

Finally, an administrator must be able to connect a project with a backend via
proper administrative commands.


Implementation details
======================
Each backend gets a `public` boolean attribute that defines whether or not it
is considered public.

Furthermore, to assign one or more backends to a project, a new
`ProjectBackend` model will be created with a primary key, a project id modeled
as string and a foreign key to `Backend` model. Since projects are kept on
Astakos's DB, no foreign key relationship can exist and so we solely rely on
Astakos not recycling project ids for data consistency. Checking for the
validity of the project's id is only helpful from a user exprerience
perspective (e.g., the administrator had a typo) but we cannot rely on this for
data consistency.  Project id and the backend id should be constrained using
`unique_together`.

When re-assigning a VM, the target project's backend set must be calculated and
if the VM's backend is not included or is not public, the operation must be
prohibited. This allows for changing a VM's project if the re-assignment does not
leave the VM on a backend it shouldn't be, but does not guarantee the
allocator's policy allocation.

The proposed administrator's command set is as follows:

*  `snf-manage project-backend-list [--project <project_id>] [--backend <backend_id>]`
   List all ProjectBackend allocations. We can use the common `--filter-by`
   option to filter the results or use the `--project` or `--backend` options
   as a shortcut to list only results for a specific project or a specific
   backend.

*  `snf-manage project-backend-add --project <project_id> --backend <backend_id>`
   Add a project backend allocation.

*  `snf-manage project-backend-remove [--project <project_id> --backend <backend_id>] <project_backend_id>`
   Remove a project backend allocation either by specifying the
   `ProjectBackend` id or a project and a backend.

The `backend-modify` command should be extended to allow setting the `public` flag.

*  `snf-manage backend-add ... --public=True|False`
*  `snf-manage backend-modify --public=True|False <backend_id>`


Future work
===========

Future work may include further decoupling the mechanism from the policy,
allowing for flexible relations to be declared and different allocation modules
to be used for defining policies. For example, cyclades may hold arbitrary
metadata for each project that may be taken into account by an allocation
module to filter possible allocation backends. Using this, a simple extension
to the above functionality is to enable policies that consider/prefer specific
and possibly restricted backends, but fall back to public ones if needed.

