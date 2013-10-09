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

from sqlalchemy import create_engine
#from sqlalchemy.event import listen
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
