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

import datetime
import copy


def split_time(value):
    """Splits time as floating point number into a tuple.

    @param value: Time in seconds
    @type value: int or float
    @return: Tuple containing (seconds, microseconds)

    """
    (seconds, microseconds) = divmod(int(value * 1000000), 1000000)

    assert 0 <= seconds, \
        "Seconds must be larger than or equal to 0, but are %s" % seconds
    assert 0 <= microseconds <= 999999, \
        "Microseconds must be 0-999999, but are %s" % microseconds

    return (int(seconds), int(microseconds))


def merge_time(timetuple):
    """Merges a tuple into a datetime object

    @param timetuple: Time as tuple, (seconds, microseconds)
    @type timetuple: tuple
    @return: Time as a datetime object

    """
    (seconds, microseconds) = timetuple

    assert 0 <= seconds, \
        "Seconds must be larger than or equal to 0, but are %s" % seconds
    assert 0 <= microseconds <= 999999, \
        "Microseconds must be 0-999999, but are %s" % microseconds

    t1 = float(seconds) + (float(microseconds) * 0.000001)
    return datetime.datetime.fromtimestamp(t1)


def case_unique(iterable):
    """
    Compare case uniquness across iterable contents. Return diff.

    >>> case_unique(['a','b','c'])
    []
    >>> case_unique(['a','A','b','c'])
    ['A']
    """
    icase = set(map(unicode.lower, unicode(iterable)))
    same = len(icase) == len(iterable)
    if not same:
        return list(set(iterable) - set(icase))

    return []


def dict_merge(a, b):
    """
    http://www.xormedia.com/recursively-merge-dictionaries-in-python/
    """
    if not isinstance(b, dict):
        return b
    result = copy.deepcopy(a)
    for k, v in b.iteritems():
        if k in result and isinstance(result[k], dict):
                result[k] = dict_merge(result[k], v)
        else:
            result[k] = copy.deepcopy(v)
    return result
