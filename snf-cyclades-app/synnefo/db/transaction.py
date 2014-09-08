# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Astakos-specific support for transactions in multiple databases. This file
# provides the entry points for the "commit_on_success"/"commit_manually"
# Django transaction functions.

"""Cyclades-specific support for transactions in multiple databases.

This file provides the entry points for the following Django transaction
functions:
 * commit_on_success
 * commit_manually
 * commit
 * rollback
"""


from django.db import transaction

from snf_django.utils.transaction import _transaction_func
from snf_django.utils.db import select_db


def commit(using=None):
    using = select_db("db") if using is None else using
    transaction.commit(using=using)


def rollback(using=None):
    using = select_db("db") if using is None else using
    transaction.rollback(using=using)


def commit_on_success(using=None):
    method = transaction.commit_on_success
    return _transaction_func("db", method, using)


def commit_manually(using=None):
    method = transaction.commit_manually
    return _transaction_func("db", method, using)
