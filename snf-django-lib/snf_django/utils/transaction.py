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

from snf_django.utils.db import select_db


def _transaction_func(app, method, using):
    """Synnefo wrapper for Django transactions.

    This function serves as a wrapper for Django transaction functions. It is
    mainly used by Synnefo transaction functions and its goal is to assist in
    using transactions in a multi-database setup.

    Arguments:
        @app: The name of app that initiates the transaction (e.g. "db", "im"),
        @method: The actual Django transaction function that will be used (e.g.
                 "commit_manually", "commit_on_success")
        @using: The database to use for the transaction (e.g. "cyclades",
                "astakos")

    Returns:
        Either a decorator/context manageer or a wrapped function, depending on
        how the aforementioned Synnefo transaction functions are called.

    To illustrate the return value, let's consider the following Cyclades
    transaction function:

    >>> from django.db import transaction
    >>> def commit_on_success(using=None):
    >>>     method = transaction.commit_on_success
    >>>     return _transaction_func("db", method, using)

    We present below two possible uses of the above function and what will
    _transaction_func return for each of them:

    1) Decorator with provided database:

    >>> @transaction.commit_on_success(using="other_db")
    >>> def func(...):
    >>>     ...

    In this case, the arguments for _transaction_func are:
        app = "db"
        method = transaction.commit_on_success
        using = "other_db"

    The returned result is the following_decorator:

        transaction.commit_on_success(using="other_db")

    2) Decorator with no database provided:

    >>> @transaction.commit_on_success
    >>> def func(...):
    >>>     ...

    In this case, the arguments for _transaction_func are:
        app = "db"
        method = transaction.commit_on_success
        using = func

    Not so surpringly, in this case the "using" argument contains the function
    to wrap instead of a database. Therefore, _transaction_func will determine
    what is the appropriate database for the app and return the decorated
    function:

        transaction.commit_on_success(using="db")(func)
    """
    db = using
    if not using or callable(using):
        db = select_db(app)

    if callable(using):
        return method(using=db)(using)
    else:
        return method(using=db)
