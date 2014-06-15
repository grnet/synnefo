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

from operator import or_
from django.db.models import Q
from synnefo.util import units
from astakos.im.models import AstakosUser


def is_resource_useful(resource, project_limit):
    """Simple function to check if the resource is useful to show.

    Values that have infinite or zero limits are discarded.
    """
    displayed_limit = units.show(project_limit, resource.unit)
    if not resource.uplimit or displayed_limit == 'inf':
        return False
    return True


def filter_name(queryset, search):
    """Filter by name using keywords.

    Since there is no single name field, we will search both in first_name,
    last_name fields.
    """
    fields = ['first_name', 'last_name']
    for term in search.split():
        criterions = (Q(**{'%s__icontains' % field: term}) for field in fields)
        qor = reduce(or_, criterions)
        queryset = queryset.filter(qor)
    return queryset


def filter_owner_name(queryset, search):
    """Filter by first name / last name of the owner.

    This filter is a bit tricky, so an explanation is due.

    The main purpose of the filter is to:
    a) Use the `filter_name` function of `users` module to find all
       the users whose name matches the search query.
    b) Use the UUIDs of the filtered users to retrieve all the entities that
       belong to them.

    What we should have in mind is that the (a) query can be a rather expensive
    one. However, the main issue here is the (b) query. For this query, a
    naive approach would be to use Q objects like so:

        Q(userid=1ae43...) | Q(userid=23bc...) | Q(userid=7be8...) | ...

    Straightforward as it may be, Django will not optimize the above expression
    into one operation but will query the database recursively. In practice, if
    the first query hasn't narrowed down the users to less than a thousand,
    this query will surely blow the stack of the database thread.

    Given that all Q objects refer to the same database field, we can bypass
    them and use the "__in" operator.  With "__in" we can pass a list of values
    (uuids in our case) as a filter argument. Moreover, we can simplify things
    a bit more by passing the queryset of (a) as the argument of "__in".  In
    Postgres, this will create a subquery, which nullifies the need to evaluate
    the results of (a) in memory and then pass them to (b).

    Warning: Querying a database using a subquery for another database has not
    been tested yet.
    """
    # Leave if no name has been given
    if not search:
        return queryset
    # Find all the uses that match the requested search term
    users = filter_name(AstakosUser.objects.all(), search).\
        values('uuid')
    # Get the related entities with the UUIDs of these users
    return queryset.filter(userid__in=users).distinct()
