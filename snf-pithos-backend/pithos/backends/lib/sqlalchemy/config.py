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

from sqlalchemy import Table, Column, String, MetaData
from sqlalchemy.sql import select
from sqlalchemy.exc import NoSuchTableError

from dbworker import DBWorker


def create_tables(engine):
    metadata = MetaData()
    columns = []
    columns.append(Column('key', String(256), primary_key=True))
    columns.append(Column('value', String(256)))
    Table('config', metadata, *columns, mysql_engine='InnoDB')

    metadata.create_all(engine)
    return metadata.sorted_tables


class Config(DBWorker):
    """Config are properties holding persistent information about system state.
    """

    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        try:
            metadata = MetaData(self.engine)
            self.config = Table('config', metadata, autoload=True)
        except NoSuchTableError:
            tables = create_tables(self.engine)
            map(lambda t: self.__setattr__(t.name, t), tables)

    def get_value(self, key):
        """Return configuration value for key."""

        s = select([self.config.c.value])
        s = s.where(self.config.c.key == key)
        r = self.conn.execute(s)
        row = r.fetchone()
        r.close()
        if row:
            return row[0]
        return None

    def set_value(self, key, value):
        """Set a configuration entry.
        """

        s = self.config.insert()
        r = self.conn.execute(s, key=key, value=value)
        inserted_primary_key = r.inserted_primary_key[0]
        r.close()
        return inserted_primary_key
