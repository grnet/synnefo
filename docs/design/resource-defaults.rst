Resource default limits and visibility
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We wish to keep track of resources which are not visible to the user or
resources that we don't care to impose a certain limit on. For example, we
wish to know the total number of CPUs per user without checking a limit and
without the user needing to specify a value when applying for a new project.
However, the administrator should be able at any time to change either of
these parameters.

Resource registration
=====================

A new resource will be registered with an infinite base quota limit (denoted
by 2**63-1). A holding is created in the quotaholder for each accepted user
with the said limit. This means that the resource is ready to be used in a
commission, but we are not interested in checking a senseful limit.

Resource ``cyclades.cpu`` will from now on denote the number of active cpus.
Its description will change to explain this. A new resource,
``cyclades.total_cpu``, will also be registered in the system, with the
semantics ``cyclades.cpu`` used to have. The reason for this change is that
(in our default policy) we would like to control the number of active CPUs
but not the total CPUs (the latter would have an infinite limit). However,
existing projects have specified a value for the resource ``cyclades.cpu``.
If we don't reinterpret it as active CPUs, then this grant will be
useless: It will add a value to infinite total CPUs, but provide no active
CPUs. Likewise we will change ``cyclades.ram`` and register
``cyclades.total_ram``.

There now exists attribute ``allow_in_projects`` in resource definitions,
which controls whether a resource appears in a project application in the
UI. Currently, this is set to False only for resource
``astakos.pending_app``. This will be renamed to ``ui_visible`` and affect
also the appearance in the Usage page. A new attribute ``api_visible`` will
also be included in resource definition (True by default), to control
whether the resource can appear in related API calls: GET /resources, GET
/quotas, POST /projects (applying for a project), etc. ``ui_visible`` will
entail ``api_visible``. Both attributes will be adjustable through
``snf-manage resource-modify``.

Resources ``cyclades.total_cpu`` and ``cyclades.total_ram`` will be marked
with ``ui_visible=False`` and ``api_visible=False``.

Changing base quota
===================

Base quota for a certain user is currently determined by looking up
the default base quota that is registered for the resource, unless there
exists a custom limit for the user/resource pair in the model
AstakosUserQuota. Resource limit can change with::

  snf-manage resource-modify <resource_name> --limit <value>

This not only changes the quota scheme for future users but also affects all
existing users that have no custom limit for this resource. This is
troublesome, because it doesn't allow simply changing the future quota
scheme. One is forced to rather set custom quota for new users, just in
order to express the new default.

This behavior will change: we will discard the distinction between users
having default or custom quota. Resource default limits will be viewed
as a skeleton for determining base quota for new users. When a new user
is accepted, resource defaults will be consulted in order to fill the
user-specific entries in AstakosUserQuota. When a resource default
changes, this will not affect quota of existing users.

For clarity, option ``--limit`` will be renamed ``--default-quota``.

We can currently change a user's base quota with::

     snf-manage user-modify <id> --set-base-quota <resource_name> <value>

This command will be extended with option ``--all`` to allow changing base
quota for multiple users; option ``--exclude`` will allow introducing
exceptions.

Inspecting base quota
=====================

Management command ``quota`` will split into ``quota-list`` and
``quota-verify``. The former will be used to list quota and will provide
various filters. Option ``--with-custom`` will allow filtering quota that
differ from the default or equal to it. Option ``--filter-by`` will enable
filtering specified values, e.g. ``--filter-by "usage>1G"``
