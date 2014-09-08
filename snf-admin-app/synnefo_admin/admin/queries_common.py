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

import functools
import logging
from operator import or_, and_

from django.db.models import Q
from django.core.exceptions import FieldError
from django.conf import settings

from synnefo_admin.admin.utils import model_dict


def prefix_strip(query):
    """Remove the prefix from the ID of Cyclades models.

    This function also returns a suggested lookup type for the stripped IDs.
    Normally, the lookup type is "contains", but if the user has entered a
    query like this:

        <prefix>4545

    the lookup type should be "startswith".
    """
    query = str(query)
    lookup_type = 'contains'
    prefix = settings.BACKEND_PREFIX_ID

    if query.startswith(prefix):
        query = query.replace(prefix, '')
        lookup_type = 'startswith'

    if not query.isdigit():
        return None, None

    return int(query), lookup_type


def get_model_field(model, query, field):
    """Get query results for a specific model field.

    This function returns the results in a list format, which can be used in
    an "IN" query easily, especially when that query will be executed in
    another database.
    """
    model = model_dict[model]
    ids = model.objects.filter(query).values_list(field, flat=True)
    return list(ids)


def model_filter(func):
    """Decorator to format query before passing it to a filter function.

    The purpose of the decorator is to:
    a) Split the queries into multiple keywords (space/tab separated).
    b) Ignore any empty queries.
    """
    @functools.wraps(func)
    def wrapper(queryset, query, *args, **kwargs):
        if isinstance(query, str) or isinstance(query, unicode):
            query = query.split()

        if query:
            try:
                return func(queryset, query, *args, **kwargs)
            except (FieldError, TypeError) as e:
                logging.error("%s", e.message)
                return queryset.none()
        else:
            return queryset

    return wrapper


def malicious(field):
    """Check if query searches in private fields."""
    if 'token' in field or 'password' in field:
        return True
    else:
        False


def update_queries(**queries):
    """Extract nested queries from a single query.

    Check if the query is actually a nested query, by searching for the "="
    operator.
    FIXME: This is not the best/cleaner/intuitive approach to do this.
    """
    new_queries = queries.copy()
    for key, value in queries.iteritems():
        if isinstance(value, str) or isinstance(value, unicode):
            nested_query = value.split('=', 1)
            if len(nested_query) == 1:
                continue
            field = nested_query[0]
            value = nested_query[1]
            if value:
                del new_queries[key]
                # Do not filter sensitive data.
                if not malicious(field):
                    new_queries[field] = value
    return new_queries


def query_list(*qobjects, **default_queries):
    """Return Q object list for the requested queries.

    This function can handle transparrently Q objects as well as simple
    queries.
    """
    queries = update_queries(**default_queries)
    lookup_type = queries.pop("lookup_type", "icontains")
    ql = list(qobjects)
    ql += [Q(**{"%s__%s" % (field, lookup_type): value})
           for field, value in queries.iteritems()]
    return ql if ql else [Q()]


def query_or(*qobjects, **queries):
    """Return ORed Q object for the requested query."""
    ql = query_list(*qobjects, **queries)
    return reduce(or_, ql)


def query_and(*qobjects, **queries):
    """Return ANDed Q object for the requested query."""
    ql = query_list(*qobjects, **queries)
    return reduce(and_, ql)


# ----------------- MODEL QUERIES --------------------#
# The following functions implement the query logic for each model

def query(model, queries):
    """Common entry point for getting a Q object for a model."""
    fun = globals().get('query_' + model)
    if fun:
        return fun(queries)
    else:
        raise Exception("Unknown model: %s" % model)


def query_user(queries):
    qor = [query_or(first_name=q, last_name=q, email=q, uuid=q)
           for q in queries]
    return query_and(*qor)


def query_vm(queries):
    qor = []
    for q in queries:
        _qor = query_or(name=q, imageid=q)
        id, lt = prefix_strip(q)
        if id:
            _qor = query_or(_qor, id=id, lookup_type=lt)
        qor.append(_qor)
    return query_and(*qor)


def query_volume(queries):
    qor = [query_or(name=q, description=q, id=q)
           for q in queries]
    return query_and(*qor)


def query_network(queries):
    qor = [query_or(name=q, id=q) for q in queries]
    return query_and(*qor)


def query_ip(queries):
    qor = [query_or(address=q) for q in queries]
    return query_and(*qor)


def query_project(queries):
    qor = [query_or(id=q, realname=q, description=q, uuid=q, homepage=q)
           for q in queries]
    return query_and(*qor)
