# Copyright (C) 2014 GRNET S.A.
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

from .common import CommonMixin
from .quota import TestQuotaMixin
from .delete_by_uuid import TestDeleteByUUIDMixin
from .snapshots import TestSnapshotsMixin

from sqlalchemy import create_engine

import os
import time

class TestSQLAlchemyBackend(CommonMixin, TestDeleteByUUIDMixin,
                            TestQuotaMixin, TestSnapshotsMixin):
    db_module = 'pithos.backends.lib.sqlalchemy'
    db_connection_str = '%(scheme)s://%(user)s:%(pwd)s@%(host)s:%(port)s/%(name)s'
    scheme = os.environ.get('DB_SCHEME', 'postgres')
    user = os.environ.get('DB_USER', 'synnefo')
    pwd = os.environ.get('DB_PWD', 'example_passw0rd')
    host = os.environ.get('DB_HOST', 'db.synnefo.live')
    port = os.environ.get('DB_PORT', 5432)
    name = 'test_pithos_backend'
    db_connection = db_connection_str % locals()
    mapfile_prefix ='snf_test_pithos_backend_sqlalchemy_%s_' % time.time()

    @classmethod
    def create_db(cls):
        db = cls.db_connection_str % {'scheme': cls.scheme, 'user': cls.user,
                                      'pwd': cls.pwd, 'host': cls.host,
                                      'port':cls.port, 'name': 'template1'}
        e = create_engine(db)
        c = e.connect()
        c.connection.connection.set_isolation_level(0)
        c.execute('create database %s' % cls.name)
        c.connection.connection.set_isolation_level(1)

    @classmethod
    def destroy_db(cls):
        db = cls.db_connection_str % {'scheme': cls.scheme, 'user': cls.user,
                                      'pwd': cls.pwd, 'host': cls.host,
                                      'port':cls.port, 'name': 'template1'}
        e = create_engine(db)
        c = e.connect()
        c.connection.connection.set_isolation_level(0)
        c.execute('drop database %s' % cls.name)
        c.connection.connection.set_isolation_level(1)

class TestSQLiteBackend(CommonMixin, TestDeleteByUUIDMixin, TestQuotaMixin,
                        TestSnapshotsMixin):
    db_module = 'pithos.backends.lib.sqlite'
    db_connection = location = '/tmp/test_pithos_backend.db'
    mapfile_prefix ='snf_test_pithos_backend_sqlite_%s_' % time.time()

    @classmethod
    def create_db(cls):
        pass

    @classmethod
    def destroy_db(cls):
        os.remove(cls.location)
