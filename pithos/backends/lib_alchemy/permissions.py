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

from sqlalchemy.sql import select, literal
from sqlalchemy.sql.expression import join, union

from xfeatures import XFeatures
from groups import Groups
from public import Public


READ = 0
WRITE = 1


class Permissions(XFeatures, Groups, Public):
    
    def __init__(self, **params):
        XFeatures.__init__(self, **params)
        Groups.__init__(self, **params)
        Public.__init__(self, **params)
    
    def access_grant(self, path, access, members=()):
        """Grant members with access to path.
           Members can also be '*' (all),
           or some group specified as 'owner:group'."""
        
        if not members:
            return
        feature = self.xfeature_create(path)
        if feature is None:
            return
        self.feature_setmany(feature, access, members)
    
    def access_set(self, path, permissions):
        """Set permissions for path. The permissions dict
           maps 'read', 'write' keys to member lists."""
        
        self.xfeature_destroy(path)
        self.access_grant(path, READ, permissions.get('read', []))
        self.access_grant(path, WRITE, permissions.get('write', []))
    
    def access_clear(self, path):
        """Revoke access to path (both permissions and public)."""
        
        self.xfeature_destroy(path)
        self.public_unset(path)
    
    def access_check(self, path, access, member):
        """Return true if the member has this access to the path."""
        
        if access == READ and self.public_check(path):
            return True
        
        r = self.xfeature_inherit(path)
        if not r:
            return False
        fpath, feature = r
        members = self.feature_get(feature, access)
        if member in members or '*' in members:
            return True
        for owner, group in self.group_parents(member):
            if owner + ':' + group in members:
                return True
        return False
    
    def access_inherit(self, path):
        """Return the inherited or assigned (path, permissions) pair for path."""
        
        r = self.xfeature_inherit(path)
        if not r:
            return (path, {})
        fpath, feature = r
        permissions = self.feature_dict(feature)
        if READ in permissions:
            permissions['read'] = permissions[READ]
            del(permissions[READ])
        if WRITE in permissions:
            permissions['write'] = permissions[WRITE]
            del(permissions[WRITE])
        return (fpath, permissions)
    
    def access_list(self, path):
        """List all permission paths inherited by or inheriting from path."""
        
        return [x[0] for x in self.xfeature_list(path) if x[0] != path]
    
    def access_list_paths(self, member, prefix=None):
        """Return the list of paths granted to member."""
        
        xfeatures_xfeaturevals =  self.xfeatures.join(self.xfeaturevals)
        
        selectable = (self.groups.c.owner + ':' + self.groups.c.name)
        member_groups = select([selectable.label('value')],
            self.groups.c.member == member)
        
        members = select([literal(member).label('value')])
        any = select([literal('*').label('value')])
        
        inner_join = join(xfeatures_xfeaturevals,
                    union(member_groups, members, any),
                    self.xfeaturevals.c.value == extended_member_groups.c.value)
        s = select([self.xfeatures.c.path], from_obj=[inner_join]).distinct()
        if prefix:
            s = s.where(self.xfeatures.c.path.like(prefix + '%'))
        r = self.conn.execute(s)
        l = [row[0] for row in r.fetchall()]
        r.close()
        return l
    
    def access_list_shared(self, prefix=''):
        """Return the list of shared paths."""
        
        s = select([self.xfeatures.c.path],
            self.xfeatures.c.path.like(prefix + '%'))
        r = self.conn.execute(s)
        l = [row[0] for row in r.fetchall()]
        r.close()
        return l
