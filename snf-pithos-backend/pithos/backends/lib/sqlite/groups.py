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

from dbworker import DBWorker


class Groups(DBWorker):
    """Groups are named collections of members, belonging to an owner."""

    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        execute = self.execute

        execute(""" create table if not exists groups
                          ( owner  text,
                            name   text,
                            member text,
                            primary key (owner, name, member) ) """)
        execute(""" create index if not exists idx_groups_member
                    on groups(member) """)

    def group_names(self, owner):
        """List all group names belonging to owner."""

        q = "select distinct name from groups where owner = ?"
        self.execute(q, (owner,))
        return [r[0] for r in self.fetchall()]

    def group_dict(self, owner):
        """Return a dict mapping group names to member lists for owner."""

        q = "select name, member from groups where owner = ?"
        self.execute(q, (owner,))
        d = defaultdict(list)
        for group, member in self.fetchall():
            d[group].append(member)
        return d

    def group_add(self, owner, group, member):
        """Add a member to a group."""

        q = ("insert or ignore into groups (owner, name, member) "
             "values (?, ?, ?)")
        self.execute(q, (owner, group, member))

    def group_addmany(self, owner, group, members):
        """Add members to a group."""

        q = ("insert or ignore into groups (owner, name, member) "
             "values (?, ?, ?)")
        self.executemany(q, ((owner, group, member) for member in members))

    def group_remove(self, owner, group, member):
        """Remove a member from a group."""

        q = "delete from groups where owner = ? and name = ? and member = ?"
        self.execute(q, (owner, group, member))

    def group_delete(self, owner, group):
        """Delete a group."""

        q = "delete from groups where owner = ? and name = ?"
        self.execute(q, (owner, group))

    def group_destroy(self, owner):
        """Delete all groups belonging to owner."""

        q = "delete from groups where owner = ?"
        self.execute(q, (owner,))

    def group_members(self, owner, group):
        """Return the list of members of a group."""

        q = "select member from groups where owner = ? and name = ?"
        self.execute(q, (owner, group))
        return [r[0] for r in self.fetchall()]

    def group_check(self, owner, group, member):
        """Check if a member is in a group."""

        q = "select 1 from groups where owner = ? and name = ? and member = ?"
        self.execute(q, (group, member))
        return bool(self.fetchone())

    def group_parents(self, member):
        """Return all (owner, group) tuples that contain member."""

        q = "select owner, name from groups where member = ?"
        self.execute(q, (member,))
        return self.fetchall()
