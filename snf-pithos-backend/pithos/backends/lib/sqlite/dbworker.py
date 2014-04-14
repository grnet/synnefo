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


class DBWorker(object):
    """Database connection handler."""

    def __init__(self, **params):
        self.params = params
        wrapper = params['wrapper']
        self.wrapper = wrapper
        conn = wrapper.conn
        cur = wrapper.conn.cursor()
        self.execute = cur.execute
        self.executemany = cur.executemany
        self.fetchone = cur.fetchone
        self.fetchall = cur.fetchall
        self.cur = cur
        self.conn = conn

    def escape_like(self, s):
        return s.replace('\\', '\\\\').replace('%', '\%').replace('_', '\_')
