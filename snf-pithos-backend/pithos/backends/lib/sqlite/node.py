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

from time import time
from operator import itemgetter
from itertools import groupby

from dbworker import DBWorker

from pithos.backends.filter import parse_filters


ROOTNODE = 0

(SERIAL, NODE, HASH, SIZE, TYPE, SOURCE, MTIME, MUSER, UUID, CHECKSUM,
 CLUSTER) = range(11)

(MATCH_PREFIX, MATCH_EXACT) = range(2)

inf = float('inf')


def strnextling(prefix):
    """Return the first unicode string
       greater than but not starting with given prefix.
       strnextling('hello') -> 'hellp'
    """
    if not prefix:
        ## all strings start with the null string,
        ## therefore we have to approximate strnextling('')
        ## with the last unicode character supported by python
        ## 0x10ffff for wide (32-bit unicode) python builds
        ## 0x00ffff for narrow (16-bit unicode) python builds
        ## We will not autodetect. 0xffff is safe enough.
        return unichr(0xffff)
    s = prefix[:-1]
    c = ord(prefix[-1])
    if c >= 0xffff:
        raise RuntimeError
    s += unichr(c + 1)
    return s


def strprevling(prefix):
    """Return an approximation of the last unicode string
       less than but not starting with given prefix.
       strprevling(u'hello') -> u'helln\\xffff'
    """
    if not prefix:
        ## There is no prevling for the null string
        return prefix
    s = prefix[:-1]
    c = ord(prefix[-1])
    if c > 0:
        s += unichr(c - 1) + unichr(0xffff)
    return s


_propnames = {
    'serial': 0,
    'node': 1,
    'hash': 2,
    'size': 3,
    'type': 4,
    'source': 5,
    'mtime': 6,
    'muser': 7,
    'uuid': 8,
    'checksum': 9,
    'cluster': 10
}


class Node(DBWorker):
    """Nodes store path organization and have multiple versions.
       Versions store object history and have multiple attributes.
       Attributes store metadata.
    """

    # TODO: Provide an interface for included and excluded clusters.

    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        execute = self.execute

        execute(""" pragma foreign_keys = on """)

        execute(""" create table if not exists nodes
                          ( node       integer primary key,
                            parent     integer default 0,
                            path       text    not null default '',
                            latest_version     integer,
                            foreign key (parent)
                            references nodes(node)
                            on update cascade
                            on delete cascade ) """)
        execute(""" create unique index if not exists idx_nodes_path
                    on nodes(path) """)
        execute(""" create index if not exists idx_nodes_parent
                    on nodes(parent) """)

        execute(""" create table if not exists policy
                          ( node   integer,
                            key    text,
                            value  text,
                            primary key (node, key)
                            foreign key (node)
                            references nodes(node)
                            on update cascade
                            on delete cascade ) """)

        execute(""" create table if not exists statistics
                          ( node       integer,
                            population integer not null default 0,
                            size       integer not null default 0,
                            mtime      integer,
                            cluster    integer not null default 0,
                            primary key (node, cluster)
                            foreign key (node)
                            references nodes(node)
                            on update cascade
                            on delete cascade ) """)

        execute(""" create table if not exists versions
                          ( serial     integer primary key,
                            node       integer,
                            hash       text,
                            size       integer not null default 0,
                            type       text    not null default '',
                            source     integer,
                            mtime      integer,
                            muser      text    not null default '',
                            uuid       text    not null default '',
                            checksum   text    not null default '',
                            cluster    integer not null default 0,
                            foreign key (node)
                            references nodes(node)
                            on update cascade
                            on delete cascade ) """)
        execute(""" create index if not exists idx_versions_node_mtime
                    on versions(node, mtime) """)
        execute(""" create index if not exists idx_versions_node_uuid
                    on versions(uuid) """)

        execute(""" create table if not exists attributes
                          ( serial      integer,
                            domain      text,
                            key         text,
                            value       text,
                            node        integer not null    default 0,
                            is_latest   boolean not null    default 1,
                            primary key (serial, domain, key)
                            foreign key (serial)
                            references versions(serial)
                            on update cascade
                            on delete cascade ) """)
        execute(""" create index if not exists idx_attributes_domain
                    on attributes(domain) """)
        execute(""" create index if not exists idx_attributes_serial_node
                    on attributes(serial, node) """)

        wrapper = self.wrapper
        wrapper.execute()
        try:
            q = "insert or ignore into nodes(node, parent) values (?, ?)"
            execute(q, (ROOTNODE, ROOTNODE))
        finally:
            wrapper.commit()

    def node_create(self, parent, path):
        """Create a new node from the given properties.
           Return the node identifier of the new node.
        """

        q = ("insert into nodes (parent, path) "
             "values (?, ?)")
        props = (parent, path)
        return self.execute(q, props).lastrowid

    def node_lookup(self, path, for_update=False):
        """Lookup the current node of the given path.
           Return None if the path is not found.

           kwargs is not used: it is passed for conformance
        """

        q = "select node from nodes where path = ?"
        self.execute(q, (path,))
        r = self.fetchone()
        if r is not None:
            return r[0]
        return None

    def node_lookup_bulk(self, paths):
        """Lookup the current nodes for the given paths.
           Return () if the path is not found.
        """

        placeholders = ','.join('?' for path in paths)
        q = "select node from nodes where path in (%s)" % placeholders
        self.execute(q, paths)
        r = self.fetchall()
        if r is not None:
            return [row[0] for row in r]
        return None

    def node_get_properties(self, node):
        """Return the node's (parent, path).
           Return None if the node is not found.
        """

        q = "select parent, path from nodes where node = ?"
        self.execute(q, (node,))
        return self.fetchone()

    def node_get_versions(self, node, keys=(), propnames=_propnames):
        """Return the properties of all versions at node.
           If keys is empty, return all properties in the order
           (serial, node, hash, size, type, source, mtime, muser, uuid, checksum, cluster).
        """

        q = ("select serial, node, hash, size, type, source, mtime, muser, uuid, checksum, cluster "
             "from versions "
             "where node = ?")
        self.execute(q, (node,))
        r = self.fetchall()
        if r is None:
            return r

        if not keys:
            return r
        return [[p[propnames[k]] for k in keys if k in propnames] for p in r]

    def node_count_children(self, node):
        """Return node's child count."""

        q = "select count(node) from nodes where parent = ? and node != 0"
        self.execute(q, (node,))
        r = self.fetchone()
        if r is None:
            return 0
        return r[0]

    def node_purge_children(self, parent, before=inf, cluster=0,
                            update_statistics_ancestors_depth=None):
        """Delete all versions with the specified
           parent and cluster, and return
           the hashes, the size and the serials of versions deleted.
           Clears out nodes with no remaining versions.
        """

        execute = self.execute
        q = ("select count(serial), sum(size) from versions "
             "where node in (select node "
             "from nodes "
             "where parent = ?) "
             "and cluster = ? "
             "and mtime <= ?")
        args = (parent, cluster, before)
        execute(q, args)
        nr, size = self.fetchone()
        if not nr:
            return (), 0, ()
        mtime = time()
        self.statistics_update(parent, -nr, -size, mtime, cluster)
        self.statistics_update_ancestors(parent, -nr, -size, mtime, cluster,
                                         update_statistics_ancestors_depth)

        q = ("select hash, serial from versions "
             "where node in (select node "
             "from nodes "
             "where parent = ?) "
             "and cluster = ? "
             "and mtime <= ?")
        execute(q, args)
        hashes = []
        serials = []
        for r in self.fetchall():
            hashes += [r[0]]
            serials += [r[1]]

        q = ("delete from versions "
             "where node in (select node "
             "from nodes "
             "where parent = ?) "
             "and cluster = ? "
             "and mtime <= ?")
        execute(q, args)
        q = ("delete from nodes "
             "where node in (select node from nodes n "
             "where (select count(serial) "
             "from versions "
             "where node = n.node) = 0 "
             "and parent = ?)")
        execute(q, (parent,))
        return hashes, size, serials

    def node_purge(self, node, before=inf, cluster=0,
                   update_statistics_ancestors_depth=None):
        """Delete all versions with the specified
           node and cluster, and return
           the hashes, the size and the serials of versions deleted.
           Clears out the node if it has no remaining versions.
        """

        execute = self.execute
        q = ("select count(serial), sum(size) from versions "
             "where node = ? "
             "and cluster = ? "
             "and mtime <= ?")
        args = (node, cluster, before)
        execute(q, args)
        nr, size = self.fetchone()
        if not nr:
            return (), 0, ()
        mtime = time()
        self.statistics_update_ancestors(node, -nr, -size, mtime, cluster,
                                         update_statistics_ancestors_depth)

        q = ("select hash, serial from versions "
             "where node = ? "
             "and cluster = ? "
             "and mtime <= ?")
        execute(q, args)
        hashes = []
        serials = []
        for r in self.fetchall():
            hashes += [r[0]]
            serials += [r[1]]

        q = ("delete from versions "
             "where node = ? "
             "and cluster = ? "
             "and mtime <= ?")
        execute(q, args)
        q = ("delete from nodes "
             "where node in (select node from nodes n "
             "where (select count(serial) "
             "from versions "
             "where node = n.node) = 0 "
             "and node = ?)")
        execute(q, (node,))
        return hashes, size, serials

    def node_remove(self, node, update_statistics_ancestors_depth=None):
        """Remove the node specified.
           Return false if the node has children or is not found.
        """

        if self.node_count_children(node):
            return False

        mtime = time()
        q = ("select count(serial), sum(size), cluster "
             "from versions "
             "where node = ? "
             "group by cluster")
        self.execute(q, (node,))
        for population, size, cluster in self.fetchall():
            self.statistics_update_ancestors(
                node, -population, -size, mtime, cluster,
                update_statistics_ancestors_depth)

        q = "delete from nodes where node = ?"
        self.execute(q, (node,))
        return True

    def node_accounts(self, accounts=()):
        q = ("select path, node from nodes where node != 0 and parent = 0 ")
        args = []
        if accounts:
            placeholders = ','.join('?' for a in accounts)
            q += ("and path in (%s)" % placeholders)
            args += accounts
        return self.execute(q, args).fetchall()

    def node_account_quotas(self):
        q = ("select n.path, p.value from nodes n, policy p "
             "where n.node != 0 and n.parent = 0 "
             "and n.node = p.node and p.key = 'quota'"
        )
        return dict(self.execute(q).fetchall())

    def node_account_usage(self, account_node, cluster):
        select_children = ("select node from nodes where parent = ?")
        select_descedents = ("select node from nodes "
                             "where parent in (%s) "
                             "or node in (%s) ") % ((select_children,)*2)
        args = [account_node]*2
        q = ("select sum(v.size) from versions v, nodes n "
             "where v.node = n.node "
             "and n.node in (%s) "
             "and v.cluster = ?") % select_descedents
        args += [cluster]

        self.execute(q, args)
        return self.fetchone()[0]

    def policy_get(self, node):
        q = "select key, value from policy where node = ?"
        self.execute(q, (node,))
        return dict(self.fetchall())

    def policy_set(self, node, policy):
        q = "insert or replace into policy (node, key, value) values (?, ?, ?)"
        self.executemany(q, ((node, k, v) for k, v in policy.iteritems()))

    def statistics_get(self, node, cluster=0):
        """Return population, total size and last mtime
           for all versions under node that belong to the cluster.
        """

        q = ("select population, size, mtime from statistics "
             "where node = ? and cluster = ?")
        self.execute(q, (node, cluster))
        return self.fetchone()

    def statistics_update(self, node, population, size, mtime, cluster=0):
        """Update the statistics of the given node.
           Statistics keep track the population, total
           size of objects and mtime in the node's namespace.
           May be zero or positive or negative numbers.
        """

        qs = ("select population, size from statistics "
              "where node = ? and cluster = ?")
        qu = ("insert or replace into statistics (node, population, size, mtime, cluster) "
              "values (?, ?, ?, ?, ?)")
        self.execute(qs, (node, cluster))
        r = self.fetchone()
        if r is None:
            prepopulation, presize = (0, 0)
        else:
            prepopulation, presize = r
        population += prepopulation
        population = max(population, 0)
        size += presize
        self.execute(qu, (node, population, size, mtime, cluster))

    def statistics_update_ancestors(self, node, population, size, mtime,
                                    cluster=0, recursion_depth=None):
        """Update the statistics of the given node's parent.
           Then recursively update all parents up to the root.
           Population is not recursive.
        """

        i = 0
        while True:
            if node == ROOTNODE:
                break
            if recursion_depth and recursion_depth <= i:
                break
            props = self.node_get_properties(node)
            if props is None:
                break
            parent, path = props
            self.statistics_update(parent, population, size, mtime, cluster)
            node = parent
            population = 0  # Population isn't recursive
            i += 1

    def statistics_latest(self, node, before=inf, except_cluster=0):
        """Return population, total size and last mtime
           for all latest versions under node that
           do not belong to the cluster.
        """

        execute = self.execute
        fetchone = self.fetchone

        # The node.
        props = self.node_get_properties(node)
        if props is None:
            return None
        parent, path = props

        # The latest version.
        q = ("select serial, node, hash, size, type, source, mtime, muser, uuid, checksum, cluster "
             "from versions v "
             "where serial = %s "
             "and cluster != ?")
        subq, args = self._construct_latest_version_subquery(
            node=node, before=before)
        execute(q % subq, args + [except_cluster])
        props = fetchone()
        if props is None:
            return None
        mtime = props[MTIME]

        # First level, just under node (get population).
        q = ("select count(serial), sum(size), max(mtime) "
             "from versions v "
             "where serial = %s "
             "and cluster != ? "
             "and node in (select node "
             "from nodes "
             "where parent = ?)")
        subq, args = self._construct_latest_version_subquery(
            node=None, before=before)
        execute(q % subq, args + [except_cluster, node])
        r = fetchone()
        if r is None:
            return None
        count = r[0]
        mtime = max(mtime, r[2])
        if count == 0:
            return (0, 0, mtime)

        # All children (get size and mtime).
        # This is why the full path is stored.
        q = ("select count(serial), sum(size), max(mtime) "
             "from versions v "
             "where serial = %s "
             "and cluster != ? "
             "and node in (select node "
             "from nodes "
             "where path like ? escape '\\')")
        subq, args = self._construct_latest_version_subquery(
            node=None, before=before)
        execute(
            q % subq, args + [except_cluster, self.escape_like(path) + '%'])
        r = fetchone()
        if r is None:
            return None
        size = r[1] - props[SIZE]
        mtime = max(mtime, r[2])
        return (count, size, mtime)

    def nodes_set_latest_version(self, node, serial):
        q = ("update nodes set latest_version = ? where node = ?")
        props = (serial, node)
        self.execute(q, props)

    def version_create(self, node, hash, size, type, source, muser, uuid,
                       checksum, cluster=0,
                       update_statistics_ancestors_depth=None):
        """Create a new version from the given properties.
           Return the (serial, mtime) of the new version.
        """

        q = ("insert into versions (node, hash, size, type, source, mtime, muser, uuid, checksum, cluster) "
             "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
        mtime = time()
        props = (node, hash, size, type, source, mtime, muser,
                 uuid, checksum, cluster)
        serial = self.execute(q, props).lastrowid
        self.statistics_update_ancestors(node, 1, size, mtime, cluster,
                                         update_statistics_ancestors_depth)

        self.nodes_set_latest_version(node, serial)

        return serial, mtime

    def version_lookup(self, node, before=inf, cluster=0, all_props=True):
        """Lookup the current version of the given node.
           Return a list with its properties:
           (serial, node, hash, size, type, source, mtime,
            muser, uuid, checksum, cluster)
           or None if the current version is not found in the given cluster.
        """

        q = ("select %s "
             "from versions v "
             "where serial = %s "
             "and cluster = ?")
        subq, args = self._construct_latest_version_subquery(
            node=node, before=before)
        if not all_props:
            q = q % ("serial", subq)
        else:
            q = q % ("serial, node, hash, size, type, source, mtime, muser, uuid, checksum, cluster", subq)

        self.execute(q, args + [cluster])
        props = self.fetchone()
        if props is not None:
            return props
        return None

    def version_lookup_bulk(self, nodes, before=inf, cluster=0, all_props=True):
        """Lookup the current versions of the given nodes.
           Return a list with their properties:
           (serial, node, hash, size, type, source, mtime, muser, uuid, checksum, cluster).
        """

        if not nodes:
            return ()
        q = ("select %s "
             "from versions "
             "where serial in %s "
             "and cluster = ? %s")
        subq, args = self._construct_latest_versions_subquery(
            nodes=nodes, before=before)
        if not all_props:
            q = q % ("serial", subq, '')
        else:
            q = q % ("serial, node, hash, size, type, source, mtime, muser, uuid, checksum, cluster", subq, 'order by node')

        args += [cluster]
        self.execute(q, args)
        return self.fetchall()

    def version_get_properties(self, serial, keys=(), propnames=_propnames):
        """Return a sequence of values for the properties of
           the version specified by serial and the keys, in the order given.
           If keys is empty, return all properties in the order
           (serial, node, hash, size, type, source, mtime, muser, uuid, checksum, cluster).
        """

        q = ("select serial, node, hash, size, type, source, mtime, muser, uuid, checksum, cluster "
             "from versions "
             "where serial = ?")
        self.execute(q, (serial,))
        r = self.fetchone()
        if r is None:
            return r

        if not keys:
            return r
        return [r[propnames[k]] for k in keys if k in propnames]

    def version_put_property(self, serial, key, value):
        """Set value for the property of version specified by key."""

        if key not in _propnames:
            return
        q = "update versions set %s = ? where serial = ?" % key
        self.execute(q, (value, serial))

    def version_recluster(self, serial, cluster,
                          update_statistics_ancestors_depth=None):
        """Move the version into another cluster."""

        props = self.version_get_properties(serial)
        if not props:
            return
        node = props[NODE]
        size = props[SIZE]
        oldcluster = props[CLUSTER]
        if cluster == oldcluster:
            return

        mtime = time()
        self.statistics_update_ancestors(node, -1, -size, mtime, oldcluster,
                                         update_statistics_ancestors_depth)
        self.statistics_update_ancestors(node, 1, size, mtime, cluster,
                                         update_statistics_ancestors_depth)

        q = "update versions set cluster = ? where serial = ?"
        self.execute(q, (cluster, serial))

    def version_remove(self, serial, update_statistics_ancestors_depth=None):
        """Remove the serial specified."""

        props = self.version_get_properties(serial)
        if not props:
            return
        node = props[NODE]
        hash = props[HASH]
        size = props[SIZE]
        cluster = props[CLUSTER]

        mtime = time()
        self.statistics_update_ancestors(node, -1, -size, mtime, cluster,
                                         update_statistics_ancestors_depth)

        q = "delete from versions where serial = ?"
        self.execute(q, (serial,))

        props = self.version_lookup(node, cluster=cluster, all_props=False)
        if props:
            self.nodes_set_latest_version(node, props[0])
        return hash, size

    def attribute_get(self, serial, domain, keys=()):
        """Return a list of (key, value) pairs of the version specified by serial.
           If keys is empty, return all attributes.
           Othwerise, return only those specified.
        """

        execute = self.execute
        if keys:
            marks = ','.join('?' for k in keys)
            q = ("select key, value from attributes "
                 "where key in (%s) and serial = ? and domain = ?" % (marks,))
            execute(q, keys + (serial, domain))
        else:
            q = "select key, value from attributes where serial = ? and domain = ?"
            execute(q, (serial, domain))
        return self.fetchall()

    def attribute_set(self, serial, domain, node, items, is_latest=True):
        """Set the attributes of the version specified by serial.
           Receive attributes as an iterable of (key, value) pairs.
        """

        q = ("insert or replace into attributes "
             "(serial, domain, node, is_latest, key, value) "
             "values (?, ?, ?, ?, ?, ?)")
        self.executemany(q, ((serial, domain, node, is_latest, k, v) for
            k, v in items))

    def attribute_del(self, serial, domain, keys=()):
        """Delete attributes of the version specified by serial.
           If keys is empty, delete all attributes.
           Otherwise delete those specified.
        """

        if keys:
            q = "delete from attributes where serial = ? and domain = ? and key = ?"
            self.executemany(q, ((serial, domain, key) for key in keys))
        else:
            q = "delete from attributes where serial = ? and domain = ?"
            self.execute(q, (serial, domain))

    def attribute_copy(self, source, dest):
        q = ("insert or replace into attributes "
             "select ?, domain, node, is_latest, key, value from attributes "
             "where serial = ?")
        self.execute(q, (dest, source))

    def attribute_unset_is_latest(self, node, exclude):
        q = ("update attributes set is_latest = 0 "
             "where node = ? and serial != ?")
        self.execute(q, (node, exclude))

    def _construct_filters(self, domain, filterq):
        if not domain or not filterq:
            return None, None

        subqlist = []
        append = subqlist.append
        included, excluded, opers = parse_filters(filterq)
        args = []

        if included:
            subq = "exists (select 1 from attributes where serial = v.serial and domain = ? and "
            subq += "(" + ' or '.join(('key = ?' for x in included)) + ")"
            subq += ")"
            args += [domain]
            args += included
            append(subq)

        if excluded:
            subq = "not exists (select 1 from attributes where serial = v.serial and domain = ? and "
            subq += "(" + ' or '.join(('key = ?' for x in excluded)) + ")"
            subq += ")"
            args += [domain]
            args += excluded
            append(subq)

        if opers:
            for k, o, v in opers:
                subq = "exists (select 1 from attributes where serial = v.serial and domain = ? and "
                subq += "key = ? and value %s ?" % (o,)
                subq += ")"
                args += [domain, k, v]
                append(subq)

        if not subqlist:
            return None, None

        subq = ' and ' + ' and '.join(subqlist)

        return subq, args

    def _construct_paths(self, pathq):
        if not pathq:
            return None, None

        subqlist = []
        args = []
        for path, match in pathq:
            if match == MATCH_PREFIX:
                subqlist.append("n.path like ? escape '\\'")
                args.append(self.escape_like(path) + '%')
            elif match == MATCH_EXACT:
                subqlist.append("n.path = ?")
                args.append(path)

        subq = ' and (' + ' or '.join(subqlist) + ')'
        args = tuple(args)

        return subq, args

    def _construct_size(self, sizeq):
        if not sizeq or len(sizeq) != 2:
            return None, None

        subq = ''
        args = []
        if sizeq[0]:
            subq += " and v.size >= ?"
            args += [sizeq[0]]
        if sizeq[1]:
            subq += " and v.size < ?"
            args += [sizeq[1]]

        return subq, args

    def _construct_versions_nodes_latest_version_subquery(self, before=inf):
        if before == inf:
            q = ("n.latest_version ")
            args = []
        else:
            q = ("(select max(serial) "
                 "from versions "
                 "where node = v.node and mtime < ?) ")
            args = [before]
        return q, args

    def _construct_latest_version_subquery(self, node=None, before=inf):
        where_cond = "node = v.node"
        args = []
        if node:
            where_cond = "node = ? "
            args = [node]

        if before == inf:
            q = ("(select latest_version "
                 "from nodes "
                 "where %s) ")
        else:
            q = ("(select max(serial) "
                 "from versions "
                 "where %s and mtime < ?) ")
            args += [before]
        return q % where_cond, args

    def _construct_latest_versions_subquery(self, nodes=(), before=inf):
        where_cond = ""
        args = []
        if nodes:
            where_cond = "node in (%s) " % ','.join('?' for node in nodes)
            args = nodes

        if before == inf:
            q = ("(select latest_version "
                 "from nodes "
                 "where %s ) ")
        else:
            q = ("(select max(serial) "
                 "from versions "
                 "where %s and mtime < ? group by node) ")
            args += [before]
        return q % where_cond, args

    def latest_attribute_keys(self, parent, domain, before=inf, except_cluster=0, pathq=None):
        """Return a list with all keys pairs defined
           for all latest versions under parent that
           do not belong to the cluster.
        """

        pathq = pathq or []

        # TODO: Use another table to store before=inf results.
        q = ("select distinct a.key "
             "from attributes a, versions v, nodes n "
             "where v.serial = %s "
             "and v.cluster != ? "
             "and v.node in (select node "
             "from nodes "
             "where parent = ?) "
             "and a.serial = v.serial "
             "and a.domain = ? "
             "and n.node = v.node")
        subq, subargs = self._construct_latest_version_subquery(
            node=None, before=before)
        args = subargs + [except_cluster, parent, domain]
        q = q % subq
        subq, subargs = self._construct_paths(pathq)
        if subq is not None:
            q += subq
            args += subargs
        self.execute(q, args)
        return [r[0] for r in self.fetchall()]

    def latest_version_list(self, parent, prefix='', delimiter=None,
                            start='', limit=10000, before=inf,
                            except_cluster=0, pathq=[], domain=None,
                            filterq=[], sizeq=None, all_props=False):
        """Return a (list of (path, serial) tuples, list of common prefixes)
           for the current versions of the paths with the given parent,
           matching the following criteria.

           The property tuple for a version is returned if all
           of these conditions are true:

                a. parent matches

                b. path > start

                c. path starts with prefix (and paths in pathq)

                d. version is the max up to before

                e. version is not in cluster

                f. the path does not have the delimiter occuring
                   after the prefix, or ends with the delimiter

                g. serial matches the attribute filter query.

                   A filter query is a comma-separated list of
                   terms in one of these three forms:

                   key
                       an attribute with this key must exist

                   !key
                       an attribute with this key must not exist

                   key ?op value
                       the attribute with this key satisfies the value
                       where ?op is one of =, != <=, >=, <, >.

                h. the size is in the range set by sizeq

           The list of common prefixes includes the prefixes
           matching up to the first delimiter after prefix,
           and are reported only once, as "virtual directories".
           The delimiter is included in the prefixes.

           If arguments are None, then the corresponding matching rule
           will always match.

           Limit applies to the first list of tuples returned.

           If all_props is True, return all properties after path, not just serial.
        """

        execute = self.execute

        if not start or start < prefix:
            start = strprevling(prefix)
        nextling = strnextling(prefix)

        q = ("select distinct n.path, %s "
             "from versions v, nodes n "
             "where v.serial = %s "
             "and v.cluster != ? "
             "and v.node in (select node "
             "from nodes "
             "where parent = ?) "
             "and n.node = v.node "
             "and n.path > ? and n.path < ?")
        subq, args = self._construct_versions_nodes_latest_version_subquery(
            before)
        if not all_props:
            q = q % ("v.serial", subq)
        else:
            q = q % ("v.serial, v.node, v.hash, v.size, v.type, v.source, v.mtime, v.muser, v.uuid, v.checksum, v.cluster", subq)
        args += [except_cluster, parent, start, nextling]
        start_index = len(args) - 2

        subq, subargs = self._construct_paths(pathq)
        if subq is not None:
            q += subq
            args += subargs
        subq, subargs = self._construct_size(sizeq)
        if subq is not None:
            q += subq
            args += subargs
        subq, subargs = self._construct_filters(domain, filterq)
        if subq is not None:
            q += subq
            args += subargs
        else:
            q = q.replace("attributes a, ", "")
            q = q.replace("and a.serial = v.serial ", "")
        q += " order by n.path"

        if not delimiter:
            q += " limit ?"
            args.append(limit)
            execute(q, args)
            return self.fetchall(), ()

        pfz = len(prefix)
        dz = len(delimiter)
        count = 0
        fetchone = self.fetchone
        prefixes = []
        pappend = prefixes.append
        matches = []
        mappend = matches.append

        execute(q, args)
        while True:
            props = fetchone()
            if props is None:
                break
            path = props[0]
            serial = props[1]
            idx = path.find(delimiter, pfz)

            if idx < 0:
                mappend(props)
                count += 1
                if count >= limit:
                    break
                continue

            if idx + dz == len(path):
                mappend(props)
                count += 1
                continue  # Get one more, in case there is a path.
            pf = path[:idx + dz]
            pappend(pf)
            if count >= limit:
                break

            args[start_index] = strnextling(pf)  # New start.
            execute(q, args)

        return matches, prefixes

    def latest_uuid(self, uuid, cluster):
        """Return the latest version of the given uuid and cluster.

        Return a (path, serial) tuple.
        If cluster is None, all clusters are considered.

        """
        if cluster is not None:
            cluster_where = "and cluster = ?"
            args = (uuid, int(cluster))
        else:
            cluster_where = ""
            args = (uuid,)

        q = ("select n.path, v.serial "
             "from versions v, nodes n "
             "where v.serial = (select max(serial) "
             "from versions "
             "where uuid = ? %s) "
             "and n.node = v.node") % cluster_where
        self.execute(q, args)
        return self.fetchone()

    def domain_object_list(self, domain, paths, cluster=None):
        """Return a list of (path, property list, attribute dictionary)
           for the objects in the specific domain and cluster.
        """

        q = ("select n.path, v.serial, v.node, v.hash, "
             "v.size, v.type, v.source, v.mtime, v.muser, "
             "v.uuid, v.checksum, v.cluster, a.key, a.value "
             "from nodes n, versions v, attributes a "
             "where v.serial = a.serial and "
             "a.domain = ? and "
             "a.node = n.node and "
             "a.is_latest = 1 and "
             "n.path in (%s)") % ','.join('?' for _ in paths)
        args = [domain]
        map(args.append, paths)
        if cluster != None:
            q += "and v.cluster = ?"
            args += [cluster]

        self.execute(q, args)
        rows = self.fetchall()

        group_by = itemgetter(slice(12))
        rows.sort(key = group_by)
        groups = groupby(rows, group_by)
        return [(k[0], k[1:], dict([i[12:] for i in data])) \
            for (k, data) in groups]
