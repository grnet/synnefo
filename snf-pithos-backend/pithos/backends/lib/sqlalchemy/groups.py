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
from sqlalchemy import Table, Column, String, MetaData
from sqlalchemy.sql import select, and_
from sqlalchemy.schema import Index
from sqlalchemy.exc import NoSuchTableError

from dbworker import DBWorker


def create_tables(engine):
    metadata = MetaData()
    columns = []
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
                   self.groups.c.owner == owner).distinct()
        r = self.conn.execute(s)
        l = [row[0] for row in r.fetchall()]
        r.close()
        return l

    def group_dict(self, owner):
        """Return a dict mapping group names to member lists for owner."""

        s = select([self.groups.c.name, self.groups.c.member],
                   self.groups.c.owner == owner)
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

    def group_addmany(self, owner, groups):
        """Add members to a group.
           Receive groups as a mapping object.
        """

        values = list({'owner': owner,
                       'name': k,
                       'member': m}
                      for k, members in groups.iteritems()
                      for m in sorted(set(members)) if m)
        if values:
            ins = self.groups.insert()
            self.conn.execute(ins, values)

    def group_remove(self, owner, group, member):
        """Remove a member from a group."""

        s = self.groups.delete().where(and_(self.groups.c.owner == owner,
                                            self.groups.c.name == group,
                                            self.groups.c.member == member))
        r = self.conn.execute(s)
        r.close()

    def group_delete(self, owner, group):
        """Delete a group."""

        s = self.groups.delete().where(and_(self.groups.c.owner == owner,
                                            self.groups.c.name == group))
        r = self.conn.execute(s)
        r.close()

    def group_destroy(self, owner):
        """Delete all groups belonging to owner."""

        s = self.groups.delete().where(self.groups.c.owner == owner)
        r = self.conn.execute(s)
        r.close()

    def group_members(self, owner, group):
        """Return the list of members of a group."""

        s = select([self.groups.c.member], and_(self.groups.c.owner == owner,
                                                self.groups.c.name == group))
        r = self.conn.execute(s)
        l = [row[0] for row in r.fetchall()]
        r.close()
        return l

    def group_check(self, owner, group, member):
        """Check if a member is in a group."""

        s = select([self.groups.c.member],
                   and_(self.groups.c.owner == owner,
                        self.groups.c.name == group,
                        self.groups.c.member == member))
        r = self.conn.execute(s)
        l = r.fetchone()
        r.close()
        return bool(l)

    def group_parents(self, member):
        """Return all (owner, group) tuples that contain member."""

        s = select([self.groups.c.owner, self.groups.c.name],
                   self.groups.c.member == member)
        r = self.conn.execute(s)
        l = r.fetchall()
        r.close()
        return l
