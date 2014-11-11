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
from synnefo_admin import admin_settings

sign = admin_settings.ADMIN_FIELD_SIGN


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
    b) Concatenate terms that have the ADMIN_FIELD_SIGN ("=") between them.
    b) Ignore any empty queries.
    """
    def process_terms(terms):
        """Generic term processing.

        This function does the following:
        * Concatenate terms that have the admin_settings.ADMIN_FIELD_SIGN ("=")
          between them. E.g. the following list:

              ['first_name', '=', 'john', 'doe', 'last_name=', 'd']

          becomes:

              ['first_name=john', 'doe', 'last_name=d']
        """
        new_terms = []
        cand = ''
        for term in terms:
            # Check if the current term can be concatenated with the previous
            # (candidate) ones.
            if term.startswith(sign) or cand.endswith(sign):
                cand = cand + term
                continue
            # If the candidate cannot be concatenated with the current term,
            # append it to the `new_terms` list.
            if cand:
                new_terms.append(cand)
            cand = term
        # Always append the last candidate, if valid
        if cand:
            new_terms.append(cand)
        return new_terms

    @functools.wraps(func)
    def wrapper(queryset, query, *args, **kwargs):
        if isinstance(query, basestring):
            query = query.split()
            query = process_terms(query)

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

    Check if the query is actually a nested query, by searching for the
    admin_settings.ADMIN_FIELD_SIGN (commonly "=").
    FIXME: This is not the best/cleaner/intuitive approach to do this.
    """
    new_queries = queries.copy()
    for key, value in queries.iteritems():
        if isinstance(value, str) or isinstance(value, unicode):
            nested_query = value.split(sign, 1)
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
