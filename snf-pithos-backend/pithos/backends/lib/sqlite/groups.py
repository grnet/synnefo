# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

    def group_addmany(self, owner, groups):
        """Add members to a group.
           Receive groups as a mapping object.
        """

        q = ("insert or ignore into groups (owner, name, member) "
             "values (?, ?, ?)")
        self.executemany(q, ((owner, group, member)
                             for group, members in groups.iteritems()
                             for member in sorted(members)))

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
