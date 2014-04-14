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

from dbworker import DBWorker


class QuotaholderSerial(DBWorker):
    """QuotaholderSerial keeps track of quota holder serials."""

    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        execute = self.execute

        execute(""" create table if not exists qh_serials
                          ( serial bigint primary key) """)

    def get_lower(self, serial):
        """Return entries lower than serial."""

        q = "select serial from qh_serials where serial < ?"
        self.execute(q, (serial,))
        return self.fetchall()

    def lookup(self, serials):
        """Return the registered serials."""

        placeholders = ','.join('?' for _ in serials)
        q = "select serial from qh_serials where serial in (%s)" % placeholders
        return [i[0] for i in self.execute(q, serials).fetchall()]

    def insert_serial(self, serial):
        """Insert a serial."""

        q = "insert or ignore into qh_serials (serial) values (?)"
        return self.execute(q, (serial,)).lastrowid

    def insert_many(self, serials):
        """Insert multiple serials."""

        q = "insert into qh_serials(serial) values (?)"
        self.executemany(q, [(s,) for s in serials])

    def delete_many(self, serials):
        """Delete specified serials."""

        if not serials:
            return
        placeholders = ','.join('?' for _ in serials)
        q = "delete from qh_serials where serial in (%s)" % placeholders
        self.conn.execute(q, serials)
