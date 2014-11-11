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

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.interfaces import PoolListener


class DBWrapper(object):
    """Database connection wrapper."""

    def __init__(self, db):
        if db.startswith('sqlite://'):
            class ForeignKeysListener(PoolListener):
                def connect(self, dbapi_con, con_record):
                    dbapi_con.execute('pragma foreign_keys=ON;')
                    dbapi_con.execute('pragma case_sensitive_like=ON;')
            self.engine = create_engine(
                db, connect_args={'check_same_thread': False},
                poolclass=NullPool, listeners=[ForeignKeysListener()],
                isolation_level='SERIALIZABLE')
        #elif db.startswith('mysql://'):
        #    db = '%s?charset=utf8&use_unicode=0' %db
        #    self.engine = create_engine(db, convert_unicode=True)
        else:
            #self.engine = create_engine(db, pool_size=0, max_overflow=-1)
            self.engine = create_engine(
                db, poolclass=NullPool, isolation_level='READ COMMITTED')
        self.engine.echo = False
        self.engine.echo_pool = False
        self.conn = self.engine.connect()
        self.trans = None

    def close(self):
        self.conn.close()
        self.conn = None

    def execute(self):
        self.trans = self.conn.begin()

    def commit(self):
        self.trans.commit()
        self.trans = None

    def rollback(self):
        self.trans.rollback()
        self.trans = None
