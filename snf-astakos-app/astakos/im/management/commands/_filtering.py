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

from synnefo.util import units
from snf_django.management.commands import CommandError
from django.db.models import Q


OP_MAP = [
    ("!=", lambda x: ~x, ""),
    (">=", lambda x: x, "__gte"),
    ("=>", lambda x: x, "__gte"),
    (">", lambda x: x, "__gt"),
    ("<=", lambda x: x, "__lte"),
    ("=<", lambda x: x, "__lte"),
    ("<", lambda x: x, "__lt"),
    ("=", lambda x: x, ""),
    ]


def parse_filter(exp):
    for s, prepend, op in OP_MAP:
        key, sep, value = exp.partition(s)
        if s == sep:
            return key, prepend, op, value
    raise CommandError("Could not parse filter.")


def make_query(flt, handlers):
    key, prepend, opstr, value = parse_filter(flt)
    try:
        (dbkey, parse) = handlers[key]
        return prepend(Q(**{dbkey+opstr: parse(value)}))
    except KeyError:
        return None


def parse_with_unit(value):
    try:
        return units.parse(value)
    except units.ParseError:
        raise CommandError("Failed to parse value, should be an integer, "
                           "possibly followed by a unit, or 'inf'.")
