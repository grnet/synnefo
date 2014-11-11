.. _multi-db-transactions:

===============================
Multi-DB transactions in Django
===============================

In this document, we will talk about Django transactions. We will explain why
transactions are a problem in a multi-db scenario and propose a way to solve
this problem.

Django transactions
===================

Django has a useful library to handle database transactions called
`transcation`.  From this library, Synnefo uses two decorators:
`commit_on_success` and `commit_manually`.

* `commit_on_success` opens a transaction with the database on enter and
  commits any queued changes on successful exit. Should an exception occur
  midway, we can rest assured that there is nothing half-committed.
* `commit_manually` opens a transaction with the database on enter but does not
  commit/rollback anything, unless explicitly told so using the
  `commit()`/`rollback()` functions.

Using these decorators as-is is fine when the Cyclades/Astakos nodes have to
deal with one database. In the case of two or more databases however, the user
needs to add the `using` argument in these decorators to define the database
that will be used to open a transaction. Else, they use the 'default' database.

Solution
========

The most straight-forward solution is to add in all decorators a `using`
argument with **cyclades** or **astakos** as database names, and enforce that
all settings from now on will have these two entries.

The only issue with this approach is that the core problem, that is, how to
chose between multiple databases in the application level, will be solved with
two different ways. The one way is with the `using` argument in transactions,
while the other one is with *database routers*.

Therefore, we propose a solution for the transaction problem that converges
with database routers.

The solution is the following:

* We will write wrappers for the `commit_on_success` and `commit_manuall`
  decorators. There will be one wrapper for Astakos and one for Cycades.  *
  When called, these wrappers will decide which is the appropriate database to
  start a transaction. The decision will use a function that is also used by
  database routers (`select_db`), and determines which is the correct db for a
  model. This is the converging point between transactions and database
  routers.
* Once the decision is made, the wrappers will return the original
  `commit_on_success` / `commit_manually` decorators, but with the chosen db
  as value of the `using` argument.

To sum up, the only changes we need to do is to add a `transaction.py` in
Astakos and Cyclades, write the wrappers and replace this import:

.. code-block:: python

    from django.db import transaction

with the Astakos/Cyclades `transaction.py` file, in any code that uses the
`commit_on_success`/`commit_manually` decorators.

