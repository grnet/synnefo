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

from dbworker import DBWorker
from sqlalchemy import Table, Column, String, MetaData
from sqlalchemy.sql import select

class Public(DBWorker):
    """Paths can be marked as public."""
    
    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        metadata = MetaData()
        columns=[]
        #columns.append(Column('path', String(2048), primary_key=True))
        columns.append(Column('path', String(255), primary_key=True))
        self.public = Table('public', metadata, *columns)
        metadata.create_all(self.engine)
        metadata.bind = self.engine
    
    
    def public_set(self, path):
        s = self.public.insert()
        r = self.conn.execute(s, path = path)
        r.close()
    
    def public_unset(self, path):
        s = self.public.delete().where(self.public.c.path == path)
        r = self.conn.execute(s)
        r.close()
    
    def public_check(self, path):
        s = select([self.public.c.path], self.public.c.path == path)
        r = self.conn.execute(s)
        l = r.fetchone()
        r.close()
        return bool(l)