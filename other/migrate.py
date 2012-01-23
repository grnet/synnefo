#!/usr/bin/env python

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
        
        columns=[]
        columns.append(Column('path', String(2048), primary_key=True))
        columns.append(Column('hash', String(255)))
        self.files = Table('files', metadata, *columns)
        self.conn = self.engine.connect()
        self.engine.echo = True
        metadata.create_all(self.engine)
    
    def put(self, path, hash):
        # Insert or replace.
        s = self.files.delete().where(self.files.c.path==path)
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
