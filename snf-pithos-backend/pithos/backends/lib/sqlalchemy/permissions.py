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

from sqlalchemy.sql import select, literal, or_
from sqlalchemy.sql.expression import join, union

from xfeatures import XFeatures
from groups import Groups
from public import Public
from node import Node

from dbworker import ESCAPE_CHAR


READ = 0
WRITE = 1


class Permissions(XFeatures, Groups, Public, Node):

    def __init__(self, **params):
        XFeatures.__init__(self, **params)
        Groups.__init__(self, **params)
        Public.__init__(self, **params)
        Node.__init__(self, **params)

    def access_grant(self, path, access, members=()):
        """Grant members with access to path.
           Members can also be '*' (all),
           or some group specified as 'owner:group'."""

        if not members:
            return
        feature = self.xfeature_create(path)
        self.feature_setmany(feature, access, members)

    def access_set(self, path, permissions):
        """Set permissions for path. The permissions dict
           maps 'read', 'write' keys to member lists."""

        r = permissions.get('read', [])
        w = permissions.get('write', [])
        if not r and not w:
            self.xfeature_destroy(path)
            return
        feature = self.xfeature_create(path)
        self.feature_clear(feature, READ)
        self.feature_clear(feature, WRITE)
        if r:
            self.feature_setmany(feature, READ, r)
        if w:
            self.feature_setmany(feature, WRITE, w)

    def access_get(self, path):
        """Get permissions for path."""

        feature = self.xfeature_get(path)
        if not feature:
            return {}
        permissions = self.feature_dict(feature)
        if READ in permissions:
            permissions['read'] = permissions[READ]
            del(permissions[READ])
        if WRITE in permissions:
            permissions['write'] = permissions[WRITE]
            del(permissions[WRITE])
        return permissions

    def access_members(self, path):
        feature = self.xfeature_get(path)
        if not feature:
            return []
        permissions = self.feature_dict(feature)
        members = set()
        members.update(permissions.get(READ, []))
        members.update(permissions.get(WRITE, []))
        for m in set(members):
            parts = m.split(':', 1)
            if len(parts) != 2:
                continue
            user, group = parts
            members.remove(m)
            members.update(self.group_members(user, group))
        return list(members)

    def access_clear(self, path):
        """Revoke access to path (both permissions and public)."""

        self.xfeature_destroy(path)
        self.public_unset(path)

    def access_clear_bulk(self, paths):
        """Revoke access to path (both permissions and public)."""

        self.xfeature_destroy_bulk(paths)
        self.public_unset_bulk(paths)

    def access_check(self, path, access, member):
        """Return true if the member has this access to the path."""

        feature = self.xfeature_get(path)
        if not feature:
            return False
        members = self.feature_get(feature, access)
        if member in members or '*' in members:
            return True
        for owner, group in self.group_parents(member):
            if owner + ':' + group in members:
                return True
        return False

    def access_inherit(self, path):
        """Return the paths influencing the access for path."""

#         r = self.xfeature_inherit(path)
#         if not r:
#             return []
#         # Compute valid.
#         return [x[0] for x in r if x[0] in valid]

        # Only keep path components.
        parts = path.rstrip('/').split('/')
        valid = []
        for i in range(1, len(parts)):
            subp = '/'.join(parts[:i + 1])
            valid.append(subp)
            if subp != path:
                valid.append(subp + '/')
        return [x for x in valid if self.xfeature_get(x)]

    def access_list_paths(self, member, prefix=None, include_owned=False,
                          include_containers=True):
        """Return the list of paths granted to member.

        Keyword arguments:
        prefix -- return only paths starting with prefix (default None)
        include_owned -- return also paths owned by member (default False)
        include_containers -- return also container paths owned by member
                              (default True)

        """

        xfeatures_xfeaturevals = self.xfeatures.join(self.xfeaturevals)

        selectable = (self.groups.c.owner + ':' + self.groups.c.name)
        member_groups = select([selectable.label('value')],
                               self.groups.c.member == member)

        members = select([literal(member).label('value')])
        any = select([literal('*').label('value')])

        u = union(member_groups, members, any).alias()
        inner_join = join(xfeatures_xfeaturevals, u,
                          self.xfeaturevals.c.value == u.c.value)
        s = select([self.xfeatures.c.path], from_obj=[inner_join]).distinct()
        if prefix:
            s = s.where(self.xfeatures.c.path.like(
                self.escape_like(prefix) + '%', escape=ESCAPE_CHAR
            ))
        r = self.conn.execute(s)
        l = [row[0] for row in r.fetchall()]
        r.close()

        if include_owned:
            container_nodes = select(
                [self.nodes.c.node],
                self.nodes.c.parent == self.node_lookup(member))
            condition = self.nodes.c.parent.in_(container_nodes)
            if include_containers:
                condition = or_(condition,
                                self.nodes.c.node.in_(container_nodes))
            s = select([self.nodes.c.path], condition)
            r = self.conn.execute(s)
            l += [row[0] for row in r.fetchall() if row[0] not in l]
            r.close()
        return l

    def access_list_shared(self, prefix=''):
        """Return the list of shared paths."""

        s = select([self.xfeatures.c.path],
                   self.xfeatures.c.path.like(self.escape_like(prefix) + '%',
                                              escape=ESCAPE_CHAR
                   )
        ).order_by(self.xfeatures.c.path.asc())
        r = self.conn.execute(s)
        l = [row[0] for row in r.fetchall()]
        r.close()
        return l
