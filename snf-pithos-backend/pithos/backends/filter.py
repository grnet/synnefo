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

import re


_regexfilter = re.compile(
    '(!?)\s*(\S+?)\s*(?:(=|!=|<=|>=|<|>)\s*(\S*?)\s*)?$', re.UNICODE)


def parse_filters(terms):
    included = []
    excluded = []
    opers = []
    match = _regexfilter.match
    for term in terms:
        m = match(term)
        if m is None:
            continue
        neg, key, op, value = m.groups()
        if neg:
            excluded.append(key)
        elif op:
            opers.append((key, op, value))
        elif not value:
            included.append(key)

    return included, excluded, opers
