#!/usr/bin/env python

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
from sqlalchemy import Table, Column, String, MetaData
from sqlalchemy.sql import select

from django.conf import settings

from pithos.backends.modular import ModularBackend


class Migration(object):
    def __init__(self, db):
        self.engine = create_engine(db)
        self.metadata = MetaData(self.engine)
        #self.engine.echo = True
        self.conn = self.engine.connect()

        options = getattr(settings, 'BACKEND', None)[1]
        self.backend = ModularBackend(*options)

    def execute(self):
        pass


class Cache():
    def __init__(self, db):
        self.engine = create_engine(db)
        metadata = MetaData(self.engine)

        columns = []
        columns.append(Column('path', String(2048), primary_key=True))
        columns.append(Column('hash', String(255)))
        self.files = Table('files', metadata, *columns)
        self.conn = self.engine.connect()
        self.engine.echo = True
        metadata.create_all(self.engine)

    def put(self, path, hash):
        # Insert or replace.
        s = self.files.delete().where(self.files.c.path == path)
        r = self.conn.execute(s)
        r.close()
        s = self.files.insert()
        r = self.conn.execute(s, {'path': path, 'hash': hash})
        r.close()

    def get(self, path):
        s = select([self.files.c.hash], self.files.c.path == path)
        r = self.conn.execute(s)
        l = r.fetchone()
        r.close()
        if not l:
            return l
        return l[0]
