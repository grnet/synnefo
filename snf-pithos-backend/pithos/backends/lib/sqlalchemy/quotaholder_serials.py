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

from sqlalchemy import Table, Column, MetaData
from sqlalchemy.types import BigInteger
from sqlalchemy.sql import select
from sqlalchemy.exc import NoSuchTableError

from dbworker import DBWorker


def create_tables(engine):
    metadata = MetaData()
    columns = []
    columns.append(Column('serial', BigInteger, primary_key=True))
    Table('qh_serials', metadata, *columns, mysql_engine='InnoDB')

    metadata.create_all(engine)
    return metadata.sorted_tables


class QuotaholderSerial(DBWorker):
    """QuotaholderSerial keeps track of quota holder serials.
    """

    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        try:
            metadata = MetaData(self.engine)
            self.qh_serials = Table('qh_serials', metadata, autoload=True)
        except NoSuchTableError:
            tables = create_tables(self.engine)
            map(lambda t: self.__setattr__(t.name, t), tables)

    def get_lower(self, serial):
        """Return entries lower than serial."""

        s = select([self.qh_serials.c.serial])
        s = s.where(self.qh_serials.c.serial < serial)
        r = self.conn.execute(s)
        rows = r.fetchall()
        r.close()
        return rows

    def lookup(self, serials):
        """Return the registered serials."""

        if not serials:
            return []
        s = select([self.qh_serials.c.serial])
        s = s.where(self.qh_serials.c.serial.in_(serials))
        r = self.conn.execute(s)
        rows = r.fetchall()
        r.close()
        return [row[0] for row in rows]

    def insert_serial(self, serial):
        """Insert a serial.
        """

        s = self.qh_serials.insert()
        r = self.conn.execute(s, serial=serial)
        r.close()

    def insert_many(self, serials):
        """Insert multiple serials.
        """

        r = self.conn.execute(
            self.qh_serials.insert(),
            list({'serial': s} for s in serials)
        )
        r.close()

    def delete_many(self, serials):
        if not serials:
            return
        st = self.qh_serials.delete().where(
            self.qh_serials.c.serial.in_(serials)
        )
        self.conn.execute(st).close()
