# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from dbworker import DBWorker
from sqlalchemy import Table, Column, String, Integer, Boolean, MetaData
from sqlalchemy.sql import and_, select
from sqlalchemy.schema import Index
from sqlalchemy.exc import NoSuchTableError


def create_tables(engine):
    metadata = MetaData()
    columns = []
    columns.append(Column('public_id', Integer, primary_key=True))
    columns.append(Column('path', String(2048), nullable=False))
    columns.append(Column('active', Boolean, nullable=False, default=True))
    public = Table('public', metadata, *columns, mysql_engine='InnoDB',
                   sqlite_autoincrement=True)
    # place an index on path
    Index('idx_public_path', public.c.path, unique=True)
    metadata.create_all(engine)
    return metadata.sorted_tables


class Public(DBWorker):
    """Paths can be marked as public."""

    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        try:
            metadata = MetaData(self.engine)
            self.public = Table('public', metadata, autoload=True)
        except NoSuchTableError:
            tables = create_tables(self.engine)
            map(lambda t: self.__setattr__(t.name, t), tables)

    def public_set(self, path):
        s = select([self.public.c.public_id])
        s = s.where(self.public.c.path == path)
        r = self.conn.execute(s)
        row = r.fetchone()
        r.close()
        if row:
            s = self.public.update().where(self.public.c.public_id == row[0])
            s = s.values(active=True)
        else:
            s = self.public.insert()
            s = s.values(path=path, active=True)
        r = self.conn.execute(s)
        r.close()

    def public_unset(self, path):
        s = self.public.update()
        s = s.where(self.public.c.path == path)
        s = s.values(active=False)
        r = self.conn.execute(s)
        r.close()

    def public_unset_bulk(self, paths):
        if not paths:
            return
        s = self.public.update()
        s = s.where(self.public.c.path.in_(paths))
        s = s.values(active=False)
        r = self.conn.execute(s)
        r.close()

    def public_get(self, path):
        s = select([self.public.c.public_id])
        s = s.where(and_(self.public.c.path == path,
                         self.public.c.active == True))
        r = self.conn.execute(s)
        row = r.fetchone()
        r.close()
        if row:
            return row[0]
        return None

    def public_list(self, prefix):
        s = select([self.public.c.path, self.public.c.public_id])
        s = s.where(self.public.c.path.like(
            self.escape_like(prefix) + '%', escape='\\'))
        s = s.where(self.public.c.active == True)
        r = self.conn.execute(s)
        rows = r.fetchall()
        r.close()
        return rows

    def public_path(self, public):
        s = select([self.public.c.path])
        s = s.where(and_(self.public.c.public_id == public,
                         self.public.c.active == True))
        r = self.conn.execute(s)
        row = r.fetchone()
        r.close()
        if row:
            return row[0]
        return None
