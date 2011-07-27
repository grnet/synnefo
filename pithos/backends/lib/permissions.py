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

from xfeatures import XFeatures
from groups import Groups
from public import Public


class Permissions(XFeatures, Groups, Public):
    
    def __init__(self, **params):
        XFeatures.__init__(self, **params)
        Groups.__init__(self, **params)
        Public.__init__(self, **params)
    
    def access_grant(self, access, path, member='all', members=()):
        """Grant a member with an access to a path."""
        xfeatures = self.xfeature_list(path)
        xfl = len(xfeatures)
        if xfl > 1 or (xfl == 1 and xfeatures[0][0] != path):
            return xfeatures
        if xfl == 0:
            feature = self.alloc_serial()
            self.xfeature_bestow(path, feature)
        else:
            fpath, feature = xfeatures[0]

        if members:
            self.feature_setmany(feature, access, members)
        else:
            self.feature_set(feature, access, member)

        return ()

    def access_revoke(self, access, path, member='all', members=()):
        """Revoke access to path from members.
           Note that this will not revoke access for members
           that are indirectly granted access through group membership.
        """
        # XXX: Maybe provide a force_revoke that will kick out
        #      all groups containing the given members?
        xfeatures = self.xfeature_list(path)
        xfl = len(xfeatures)
        if xfl != 1 or xfeatures[0][0] != path:
            return xfeatures

        fpath, feature = xfeatures[0]

        if members:
            self.feature_unsetmany(feature, access, members=members)
        else:
            self.feature_unset(feature, access, member)

        # XXX: provide a meaningful return value? 

        return ()

    def access_check(self, access, path, member):
        """Return true if the member has this access to the path."""
        r = self.xfeature_inherit(path)
        if not r:
            return 0

        fpath, feature = r
        memberset = set(self.feature_get(feature, access))
        if member in memberset:
            return 1

        for group in self.group_parents(self, member):
            if group in memberset:
                return 1

        return 0

    def access_list(self, path):
        """Return the list of (access, member) pairs for the path."""
        r = self.xfeature_inherit(path)
        if not r:
            return ()

        fpath, feature = r
        return self.feature_list(feature)

    def access_list_paths(self, member):
        """Return the list of (access, path) pairs granted to member."""
        q = ("select distinct key, path from xfeatures inner join "
             "   (select distinct feature, key from xfeaturevals inner join "
             "      (select name as value from members "
             "       where member = ? union select ?) "
             "    using (value)) "
             "using (feature)")

        self.execute(q, (member, member))
        return self.fetchall()
