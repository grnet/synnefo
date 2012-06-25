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


class Public(DBWorker):
    """Paths can be marked as public."""
    
    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        execute = self.execute
        
        execute(""" create table if not exists public
                          ( public_id integer primary key autoincrement,
                            path      text not null,
                            active    boolean not null default 1 ) """)
        execute(""" create unique index if not exists idx_public_path
                    on public(path) """)
    
    def public_set(self, path):
        q = "insert or ignore into public (path) values (?)"
        self.execute(q, (path,))
        q = "update public set active = 1 where path = ?"
        self.execute(q, (path,))
    
    def public_unset(self, path):
        q = "update public set active = 0 where path = ?"
        self.execute(q, (path,))
    
    def public_unset_bulk(self, paths):
        placeholders = ','.join('?' for path in paths)
        q = "update public set active = 0 where path in (%s)" % placeholders
        self.execute(q, paths)
    
    def public_get(self, path):
        q = "select public_id from public where path = ? and active = 1"
        self.execute(q, (path,))
        row = self.fetchone()
        if row:
            return row[0]
        return None
    
    def public_list(self, prefix):
        q = "select path, public_id from public where path like ? escape '\\' and active = 1"
        self.execute(q, (self.escape_like(prefix) + '%',))
        return self.fetchall()
    
    def public_path(self, public):
        q = "select path from public where public_id = ? and active = 1"
        self.execute(q, (public,))
        row = self.fetchone()
        if row:
            return row[0]
        return None
