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

from collections import defaultdict
from sqlalchemy import Table, Column, String, MetaData
from sqlalchemy.sql import select, and_
from sqlalchemy.schema import Index
from sqlalchemy.exc import NoSuchTableError

from dbworker import DBWorker

def create_tables(engine):
    metadata = MetaData()
    columns=[]
    columns.append(Column('owner', String(256), primary_key=True))
    columns.append(Column('name', String(256), primary_key=True))
    columns.append(Column('member', String(256), primary_key=True))
    groups = Table('groups', metadata, *columns, mysql_engine='InnoDB')
    
    # place an index on member
    Index('idx_groups_member', groups.c.member)
        
    metadata.create_all(engine)
    return metadata.sorted_tables
    
class Groups(DBWorker):
    """Groups are named collections of members, belonging to an owner."""
    
    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        try:
            metadata = MetaData(self.engine)
            self.groups = Table('groups', metadata, autoload=True)
        except NoSuchTableError:
            tables = create_tables(self.engine)
            map(lambda t: self.__setattr__(t.name, t), tables)
        
    def group_names(self, owner):
        """List all group names belonging to owner."""
        
        s = select([self.groups.c.name],
            self.groups.c.owner==owner).distinct()
        r = self.conn.execute(s)
        l = [row[0] for row in r.fetchall()]
        r.close()
        return l
    
    def group_dict(self, owner):
        """Return a dict mapping group names to member lists for owner."""
        
        s = select([self.groups.c.name, self.groups.c.member],
            self.groups.c.owner==owner)
        r = self.conn.execute(s)
        d = defaultdict(list)
        for group, member in r.fetchall():
            d[group].append(member)
        r.close()
        return d
    
    def group_add(self, owner, group, member):
        """Add a member to a group."""
        
        s = self.groups.select()
        s = s.where(self.groups.c.owner == owner)
        s = s.where(self.groups.c.name == group)
        s = s.where(self.groups.c.member == member)
        r = self.conn.execute(s)
        groups = r.fetchall()
        r.close()
        if len(groups) == 0:    
            s = self.groups.insert()
            r = self.conn.execute(s, owner=owner, name=group, member=member)
            r.close()
    
    def group_addmany(self, owner, group, members):
        """Add members to a group."""
        
        #TODO: more efficient way to do it
        for member in members:
            self.group_add(owner, group, member)
    
    def group_remove(self, owner, group, member):
        """Remove a member from a group."""
        
        s = self.groups.delete().where(and_(self.groups.c.owner==owner,
                                            self.groups.c.name==group,
                                            self.groups.c.member==member))
        r = self.conn.execute(s)
        r.close()
    
    def group_delete(self, owner, group):
        """Delete a group."""
        
        s = self.groups.delete().where(and_(self.groups.c.owner==owner,
                                            self.groups.c.name==group))
        r = self.conn.execute(s)
        r.close()
    
    def group_destroy(self, owner):
        """Delete all groups belonging to owner."""
        
        s = self.groups.delete().where(self.groups.c.owner==owner)
        r = self.conn.execute(s)
        r.close()
    
    def group_members(self, owner, group):
        """Return the list of members of a group."""
        
        s = select([self.groups.c.member], and_(self.groups.c.owner==owner,
                                                self.groups.c.name==group))
        r = self.conn.execute(s)
        l = [row[0] for row in r.fetchall()]
        r.close()
        return l
    
    def group_check(self, owner, group, member):
        """Check if a member is in a group."""
        
        s = select([self.groups.c.member], and_(self.groups.c.owner==owner,
                           self.groups.c.name==group,
                           self.groups.c.member==member))
        r = self.conn.execute(s)
        l = r.fetchone()
        r.close()
        return bool(l)
    
    def group_parents(self, member):
        """Return all (owner, group) tuples that contain member."""
        
        s = select([self.groups.c.owner, self.groups.c.name],
            self.groups.c.member==member)
        r = self.conn.execute(s)
        l = r.fetchall()
        r.close()
        return l
