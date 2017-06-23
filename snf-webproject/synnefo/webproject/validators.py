# Copyright (C) 2016 GRNET S.A.
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

"""This module hosts code for request validation purposes"""

import re
import unicodedata


def whitespace(char):
    """Returns True if char is a whitespace"""
    return unicodedata.category(char).startswith("Z")


def non_printable(char):
    """Returns True if char is non printable"""
    category = unicodedata.category(char)
    return category.startswith("C") or (category in ("Zl", "Zp"))


def printable_char_range(allow_ws=True, exclude=(), invert=False):
    """Returns a set of printable characters to be used in regular expressions.
       allow_ws: Allow whitespace characters
       exclude: Set of characters to exclude from the returned ranges
       invert: Invert the character set
    """

    def non_valid(char):
        """Returns True if char is a non allowed character"""
        result = char in exclude or non_printable(char) or \
            (whitespace(char) and allow_ws is False)
        return result if not invert else not result

    in_range = False
    result = u''
    start = last = None
    # We only check the Basic Multilingual Plane (plane 0)
    for i in xrange(0xFFFF):
        char = unichr(i)
        if non_valid(char):
            if in_range and last != start:
                result += "-%s" % re.escape(last)
            in_range = False
            continue

        last = char
        if not in_range:
            result += re.escape(char)
            start = char
            in_range = True

    if in_range:
        result += "-%s" % re.escape(last)

    return result
