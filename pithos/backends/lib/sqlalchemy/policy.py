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

from sqlalchemy import Table, Column, String, MetaData
from sqlalchemy.sql import select
from sqlalchemy.sql import and_
from dbworker import DBWorker


class Policy(DBWorker):
    """Paths can be assigned key, value pairs, representing policy."""
    
    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        metadata = MetaData()
        columns=[]
        columns.append(Column('path', String(2048), index=True))
        columns.append(Column('key', String(255)))
        columns.append(Column('value', String(255)))
        self.policies = Table('policy', metadata, *columns, mysql_engine='InnoDB')
        metadata.create_all(self.engine)
    
    def policy_set(self, path, policy):
        #insert or replace
        for k, v in policy.iteritems():
            s = self.policies.update().where(and_(self.policies.c.path == path,
                                                  self.policies.c.key == k))
            s = s.values(value = v)
            rp = self.conn.execute(s)
            rp.close()
            if rp.rowcount == 0:
                s = self.policies.insert()
                values = {'path':path, 'key':k, 'value':v}
                r = self.conn.execute(s, values)
                r.close()
    
    def policy_unset(self, path):
        s = self.policies.delete().where(self.policies.c.path==path)
        r = self.conn.execute(s)
        r.close()
    
    def policy_get(self, path):
        s = select([self.policies.c.key, self.policies.c.value],
            self.policies.c.path==self.policies.c.path==path)
        r = self.conn.execute(s)
        d = dict(r.fetchall())
        r.close()
        return d