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

try:
    from pysqlite2 import dbapi2 as sqlite3
except ImportError:
    import sqlite3


class DBWrapper(object):
    """Database connection wrapper."""

    def __init__(self, db):
        self.conn = sqlite3.connect(db, check_same_thread=False)
        self.conn.execute(""" pragma case_sensitive_like = on """)

    def close(self):
        self.conn.close()

    def execute(self):
        self.conn.execute('begin deferred')

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()
