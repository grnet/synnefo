# Copyright (C) 2010-2017 GRNET S.A.
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

from snf_django.utils.db import select_db
from django.db import transaction


class NonNestedAtomic(transaction.Atomic):
    def __enter__(self):
        connection = transaction.get_connection(self.using)
        connection.validate_no_atomic_block()
        transaction.Atomic.__enter__(self)


def atomic(app, using, savepoint):
    """Synnefo wrapper for Django atomic transactions.

    This function serves as a wrapper for Django atomic(). Its goal is to
    assist in using transactions in a multi-database setup.

    We explicitly forbid nested transactions --- we need to be sure that an
    atomic block really commits to the database rather than acting as a
    savepoint for an outer atomic block.
    """
    db = select_db(app) if not using or callable(using) else using
    ctx = NonNestedAtomic(db, savepoint)
    return ctx(using) if callable(using) else ctx
