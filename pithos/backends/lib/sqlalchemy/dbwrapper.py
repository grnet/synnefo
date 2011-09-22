# Copyright 2011 GRNET S.A. All rights reserved.
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

from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool

class DBWrapper(object):
    """Database connection wrapper."""
    
    def __init__(self, db):
        if db.startswith('sqlite://'):
            def my_on_connect(dbapi_conn, connection_rec, connection_proxy):
                db_cursor = dbapi_conn.execute('pragma foreign_keys=ON')
            self.engine = create_engine(db, connect_args={'check_same_thread': False}, poolclass=NullPool)
            event.listen(self.engine, 'checkout', my_on_connect)
        else:
            self.engine = create_engine(db)
        #self.engine.echo = True
        self.conn = self.engine.connect()
        self.trans = None
    
    def execute(self):
        self.trans = self.conn.begin()
    
    def commit(self):
        self.trans.commit()
        self.trans = None
    
    def rollback(self):
        self.trans.rollback()
        self.trans = None
