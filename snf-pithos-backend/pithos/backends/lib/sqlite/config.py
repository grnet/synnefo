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

# from collections import defaultdict
#
from dbworker import DBWorker


class Config(DBWorker):
    """Config are properties holding persistent information about system state.
    """

    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        execute = self.execute

        execute(""" create table if not exists config
                          ( key text primary key,
                            value text ) """)

    def get_value(self, key):
        """Return configuration value for key."""

        q = "select value from config where key = ?"
        self.execute(q, (key,))
        r = self.fetchone()
        if r is not None:
            return r[0]
        return None

    def set_value(self, key, value):
        """Set configuration entry.
        """

        q = "insert into config (key, value) values (?, ?)"
        id = self.execute(q, (key, value)).lastrowid
        return id
