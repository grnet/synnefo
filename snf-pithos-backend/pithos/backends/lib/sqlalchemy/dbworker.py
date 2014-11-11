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

ESCAPE_CHAR = '@'


class DBWorker(object):
    """Database connection handler."""

    def __init__(self, **params):
        self.params = params
        wrapper = params['wrapper']
        self.wrapper = wrapper
        self.conn = wrapper.conn
        self.engine = wrapper.engine

    def escape_like(self, s, escape_char=ESCAPE_CHAR):
        return (s.replace(escape_char, escape_char * 2).
                replace('%', escape_char + '%').
                replace('_', escape_char + '_'))
