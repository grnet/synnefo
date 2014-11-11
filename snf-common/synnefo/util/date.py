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

from datetime import timedelta, tzinfo

import dateutil.parser


class UTC(tzinfo):
    """
    Helper UTC time information object.
    """

    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return 'UTC'

    def dst(self, dt):
        return timedelta(0)


def isoformat(d):
    """
    Return an ISO8601 date string that includes a timezone.

    >>> from datetime import datetime
    >>> d = datetime(2012, 8, 10, 00, 59, 59)
    >>> isoformat(d)
    '2012-08-10T00:59:59+00:00'
    """

    return d.replace(tzinfo=UTC()).isoformat()


def isoparse(s):
    """
    Parse an ISO8601 date string into a datetime object.

    >>> isoparse('2012-08-10T00:59:59+00:00')
    datetime.datetime(2012, 8, 10, 0, 59, 59)
    """

    since = dateutil.parser.parse(s)
    utc_since = since.astimezone(UTC()).replace(tzinfo=None)
    return utc_since
