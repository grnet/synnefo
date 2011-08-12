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

from time import time
from sqlalchemy import Table, Integer, Column, String, MetaData, ForeignKey
from sqlalchemy.schema import Index, Sequence
from sqlalchemy.sql import func, and_, null
from sqlalchemy.sql import select

from dbworker import DBWorker


ROOTNODE  = 1

( SERIAL, NODE, SIZE, SOURCE, MTIME, MUSER, CLUSTER ) = range(7)

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
    s += unichr(c+1)
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
        s += unichr(c-1) + unichr(0xffff)
    return s


_propnames = {
    'serial'    : 0,
    'node'      : 1,
    'size'      : 2,
    'source'    : 3,
    'mtime'     : 4,
    'muser'     : 5,
    'cluster'   : 6,
}


class Node(DBWorker):
    """Nodes store path organization and have multiple versions.
       Versions store object history and have multiple attributes.
       Attributes store metadata.
    """
    
    # TODO: Provide an interface for included and excluded clusters.
    
    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        metadata = MetaData()
        
        #create nodes table
        columns=[]
        columns.append(Column('node', Integer, primary_key=True))
        columns.append(Column('parent', Integer,
                              ForeignKey('nodes.node',
                                         ondelete='CASCADE',
                                         onupdate='CASCADE'),
                              autoincrement=False))
        #columns.append(Column('path', String(2048), default='', nullable=False))
        columns.append(Column('path', String(255), default='', nullable=False))
        self.nodes = Table('nodes', metadata, *columns)
        # place an index on path
        Index('idx_nodes_path', self.nodes.c.path, unique=True)
        
        #create statistics table
        columns=[]
        columns.append(Column('node', Integer,
                              ForeignKey('nodes.node',
                                         ondelete='CASCADE',
                                         onupdate='CASCADE'),
                              primary_key=True))
        columns.append(Column('population', Integer, nullable=False, default=0))
        columns.append(Column('size', Integer, nullable=False, default=0))
        columns.append(Column('mtime', Integer))
        columns.append(Column('cluster', Integer, nullable=False, default=0,
                              primary_key=True))
        self.statistics = Table('statistics', metadata, *columns)
        
        #create versions table
        columns=[]
        columns.append(Column('serial', Integer, primary_key=True))
        columns.append(Column('node', Integer,
                              ForeignKey('nodes.node',
                                         ondelete='CASCADE',
                                         onupdate='CASCADE')))
        columns.append(Column('size', Integer, nullable=False, default=0))
        columns.append(Column('source', Integer))
        columns.append(Column('mtime', Integer))
        columns.append(Column('muser', String(255), nullable=False, default=''))
        columns.append(Column('cluster', Integer, nullable=False, default=0))
        self.versions = Table('versions', metadata, *columns)
        # place an index on node
        Index('idx_versions_node', self.versions.c.node)
        # TODO: Sort out if more indexes are needed.
        #Index('idx_versions_node', self.versions.c.mtime)
        
        #create attributes table
        columns = []
        columns.append(Column('serial', Integer,
                              ForeignKey('versions.serial',
                                         ondelete='CASCADE',
                                         onupdate='CASCADE'),
                              primary_key=True))
        columns.append(Column('key', String(255), primary_key=True))
        columns.append(Column('value', String(255)))
        self.attributes = Table('attributes', metadata, *columns)
        
        metadata.create_all(self.engine)
        
        s = self.nodes.select().where(and_(self.nodes.c.node == 1,
                                           self.nodes.c.parent == 1))
        r = self.conn.execute(s).fetchone()
        if not r:
            s = self.nodes.insert().values(node=ROOTNODE, parent=ROOTNODE)
            self.conn.execute(s)
    
    def node_create(self, parent, path):
        """Create a new node from the given properties.
           Return the node identifier of the new node.
        """
        #TODO catch IntegrityError?
        s = self.nodes.insert().values(parent=parent, path=path)
        r = self.conn.execute(s)
        inserted_primary_key = r.inserted_primary_key[0]
        r.close()
        return inserted_primary_key
    
    def node_lookup(self, path):
        """Lookup the current node of the given path.
           Return None if the path is not found.
        """
        
        s = select([self.nodes.c.node], self.nodes.c.path == path)
        r = self.conn.execute(s)
        row = r.fetchone()
        r.close()
        if row:
            return row[0]
        return None
    
    def node_get_properties(self, node):
        """Return the node's (parent, path).
           Return None if the node is not found.
        """
        
        s = select([self.nodes.c.parent, self.nodes.c.path])
        s = s.where(self.nodes.c.node == node)
        r = self.conn.execute(s)
        l = r.fetchone()
        r.close()
        return l
    
    def node_get_versions(self, node, keys=(), propnames=_propnames):
        """Return the properties of all versions at node.
           If keys is empty, return all properties in the order
           (serial, node, size, source, mtime, muser, cluster).
        """
        
        s = select(['*'], self.versions.c.node == node)
        r = self.conn.execute(s)
        rows = r.fetchall()
        if not rows:
            return rows
        
        if not keys:
            return rows
        
        return [[p[propnames[k]] for k in keys if k in propnames] for p in rows]
    
    def node_count_children(self, node):
        """Return node's child count."""
        
        s = select([func.count(self.nodes.c.node)])
        s = s.where(and_(self.nodes.c.parent == node,
                         self.nodes.c.node != ROOTNODE))
        r = self.conn.execute(s)
        row = r.fetchone()
        r.close()
        return row[0]
    
    def node_purge_children(self, parent, before=inf, cluster=0):
        """Delete all versions with the specified
           parent and cluster, and return
           the serials of versions deleted.
           Clears out nodes with no remaining versions.
        """
        
        scalar = select([self.nodes.c.node],
            self.nodes.c.parent == parent).as_scalar()
        where_clause = and_(self.versions.c.node.in_(scalar),
                            self.versions.c.cluster == cluster,
                            "versions.mtime <= %f" %before)
        s = select([func.count(self.versions.c.serial),
                    func.sum(self.versions.c.size)])
        s = s.where(where_clause)
        r = self.conn.execute(s)
        row = r.fetchone()
        r.close()
        if not row:
            return ()
        nr, size = row[0], -row[1] if row[1] else 0
        mtime = time()
        print '#', parent, -nr, size, mtime, cluster
        self.statistics_update(parent, -nr, size, mtime, cluster)
        self.statistics_update_ancestors(parent, -nr, size, mtime, cluster)
        
        s = select([self.versions.c.serial])
        s = s.where(where_clause)
        r = self.conn.execute(s)
        serials = [row[SERIAL] for row in r.fetchall()]
        r.close()
        
        #delete versiosn
        s = self.versions.delete().where(where_clause)
        r = self.conn.execute(s)
        r.close()
        
        #delete nodes
        a = self.nodes.alias()
        no_versions = select([func.count(self.versions.c.serial)],
            self.versions.c.node == a.c.node).as_scalar() == 0
        n = select([self.nodes.c.node],
            and_(no_versions, self.nodes.c.parent == parent))
        s = s.where(self.nodes.c.node.in_(n))
        s = self.nodes.delete().where(self.nodes.c.node == s)
        print '#', s
        self.conn.execute(s).close()
        return serials
    
    def node_purge(self, node, before=inf, cluster=0):
        """Delete all versions with the specified
           node and cluster, and return
           the serials of versions deleted.
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
            return ()
        mtime = time()
        self.statistics_update_ancestors(node, -nr, -size, mtime, cluster)
        
        q = ("select serial from versions "
             "where node = ? "
             "and cluster = ? "
             "and mtime <= ?")
        execute(q, args)
        serials = [r[SERIAL] for r in self.fetchall()]
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
        return serials
    
    def node_remove(self, node):
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
            self.statistics_update_ancestors(node, -population, -size, mtime, cluster)
        
        q = "delete from nodes where node = ?"
        self.execute(q, (node,))
        return True
    
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
        
        s = select([self.statistics.c.population, self.statistics.c.size],
            and_(self.statistics.c.node == node,
                 self.statistics.c.cluster == cluster))
        res = self.conn.execute(s)
        r = res.fetchone()
        res.close()
        if not r:
            prepopulation, presize = (0, 0)
        else:
            prepopulation, presize = r
        population += prepopulation
        size += presize
        
        self.statistics.insert().values(node=node, population=population,
                                        size=size, mtime=mtime, cluster=cluster)
        self.conn.execute(s).close()
    
    def statistics_update_ancestors(self, node, population, size, mtime, cluster=0):
        """Update the statistics of the given node's parent.
           Then recursively update all parents up to the root.
           Population is not recursive.
        """
        
        while True:
            if node == ROOTNODE:
                break
            props = self.node_get_properties(node)
            if props is None:
                break
            parent, path = props
            self.statistics_update(parent, population, size, mtime, cluster)
            node = parent
            population = 0 # Population isn't recursive
    
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
        q = ("select serial, node, size, source, mtime, muser, cluster "
             "from versions "
             "where serial = (select max(serial) "
                             "from versions "
                             "where node = ? and mtime < ?) "
             "and cluster != ?")
        execute(q, (node, before, except_cluster))
        props = fetchone()
        if props is None:
            return None
        mtime = props[MTIME]
        
        # First level, just under node (get population).
        q = ("select count(serial), sum(size), max(mtime) "
             "from versions v "
             "where serial = (select max(serial) "
                             "from versions "
                             "where node = v.node and mtime < ?) "
             "and cluster != ? "
             "and node in (select node "
                          "from nodes "
                          "where parent = ?)")
        execute(q, (before, except_cluster, node))
        r = fetchone()
        if r is None:
            return None
        count = r[0]
        mtime = max(mtime, r[2])
        if count == 0:
            return (0, 0, mtime)
        
        # All children (get size and mtime).
        # XXX: This is why the full path is stored.
        q = ("select count(serial), sum(size), max(mtime) "
             "from versions v "
             "where serial = (select max(serial) "
                             "from versions "
                             "where node = v.node and mtime < ?) "
             "and cluster != ? "
             "and node in (select node "
                          "from nodes "
                          "where path like ?)")
        execute(q, (before, except_cluster, path + '%'))
        r = fetchone()
        if r is None:
            return None
        size = r[1] - props[SIZE]
        mtime = max(mtime, r[2])
        return (count, size, mtime)
    
    def version_create(self, node, size, source, muser, cluster=0):
        """Create a new version from the given properties.
           Return the (serial, mtime) of the new version.
        """
        
        q = ("insert into versions (node, size, source, mtime, muser, cluster) "
             "values (?, ?, ?, ?, ?, ?)")
        mtime = time()
        props = (node, size, source, mtime, muser, cluster)
        serial = self.execute(q, props).lastrowid
        self.statistics_update_ancestors(node, 1, size, mtime, cluster)
        return serial, mtime
    
    def version_lookup(self, node, before=inf, cluster=0):
        """Lookup the current version of the given node.
           Return a list with its properties:
           (serial, node, size, source, mtime, muser, cluster)
           or None if the current version is not found in the given cluster.
        """
        
        q = ("select serial, node, size, source, mtime, muser, cluster "
             "from versions "
             "where serial = (select max(serial) "
                             "from versions "
                             "where node = ? and mtime < ?) "
             "and cluster = ?")
        self.execute(q, (node, before, cluster))
        props = self.fetchone()
        if props is not None:
            return props
        return None
    
    def version_get_properties(self, serial, keys=(), propnames=_propnames):
        """Return a sequence of values for the properties of
           the version specified by serial and the keys, in the order given.
           If keys is empty, return all properties in the order
           (serial, node, size, source, mtime, muser, cluster).
        """
        
        q = ("select serial, node, size, source, mtime, muser, cluster "
             "from versions "
             "where serial = ?")
        self.execute(q, (serial,))
        r = self.fetchone()
        if r is None:
            return r
        
        if not keys:
            return r
        return [r[propnames[k]] for k in keys if k in propnames]
    
    def version_recluster(self, serial, cluster):
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
        self.statistics_update_ancestors(node, -1, -size, mtime, oldcluster)
        self.statistics_update_ancestors(node, 1, size, mtime, cluster)
        
        q = "update versions set cluster = ? where serial = ?"
        self.execute(q, (cluster, serial))
    
    def version_remove(self, serial):
        """Remove the serial specified."""
        
        props = self.node_get_properties(serial)
        if not props:
            return
        node = props[NODE]
        size = props[SIZE]
        cluster = props[CLUSTER]
        
        mtime = time()
        self.statistics_update_ancestors(node, -1, -size, mtime, cluster)
        
        q = "delete from versions where serial = ?"
        self.execute(q, (serial,))
        return True
    
    def attribute_get(self, serial, keys=()):
        """Return a list of (key, value) pairs of the version specified by serial.
           If keys is empty, return all attributes.
           Othwerise, return only those specified.
        """
        
        execute = self.execute
        if keys:
            marks = ','.join('?' for k in keys)
            q = ("select key, value from attributes "
                 "where key in (%s) and serial = ?" % (marks,))
            execute(q, keys + (serial,))
        else:
            q = "select key, value from attributes where serial = ?"
            execute(q, (serial,))
        return self.fetchall()
    
    def attribute_set(self, serial, items):
        """Set the attributes of the version specified by serial.
           Receive attributes as an iterable of (key, value) pairs.
        """
        
        q = ("insert or replace into attributes (serial, key, value) "
             "values (?, ?, ?)")
        self.executemany(q, ((serial, k, v) for k, v in items))
    
    def attribute_del(self, serial, keys=()):
        """Delete attributes of the version specified by serial.
           If keys is empty, delete all attributes.
           Otherwise delete those specified.
        """
        
        if keys:
            q = "delete from attributes where serial = ? and key = ?"
            self.executemany(q, ((serial, key) for key in keys))
        else:
            q = "delete from attributes where serial = ?"
            self.execute(q, (serial,))
    
    def attribute_copy(self, source, dest):
        q = ("insert or replace into attributes "
             "select ?, key, value from attributes "
             "where serial = ?")
        self.execute(q, (dest, source))
    
    def _construct_filters(self, filterq):
        if not filterq:
            return None, None
        
        args = filterq.split(',')
        subq = " and a.key in ("
        subq += ','.join(('?' for x in args))
        subq += ")"
        
        return subq, args
    
    def _construct_paths(self, pathq):
        if not pathq:
            return None, None
        
        subq = " and ("
        subq += ' or '.join(('n.path like ?' for x in pathq))
        subq += ")"
        args = tuple([x + '%' for x in pathq])
        
        return subq, args
    
    def latest_attribute_keys(self, parent, before=inf, except_cluster=0, pathq=[]):
        """Return a list with all keys pairs defined
           for all latest versions under parent that
           do not belong to the cluster.
        """
        
        # TODO: Use another table to store before=inf results.
        q = ("select distinct a.key "
             "from attributes a, versions v, nodes n "
             "where v.serial = (select max(serial) "
                              "from versions "
                              "where node = v.node and mtime < ?) "
             "and v.cluster != ? "
             "and v.node in (select node "
                           "from nodes "
                           "where parent = ?) "
             "and a.serial = v.serial "
             "and n.node = v.node")
        args = (before, except_cluster, parent)
        subq, subargs = self._construct_paths(pathq)
        if subq is not None:
            q += subq
            args += subargs
        self.execute(q, args)
        return [r[0] for r in self.fetchall()]
    
    def latest_version_list(self, parent, prefix='', delimiter=None,
                            start='', limit=10000, before=inf,
                            except_cluster=0, pathq=[], filterq=None):
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
                       where ?op is one of ==, != <=, >=, <, >.
           
           The list of common prefixes includes the prefixes
           matching up to the first delimiter after prefix,
           and are reported only once, as "virtual directories".
           The delimiter is included in the prefixes.
           
           If arguments are None, then the corresponding matching rule
           will always match.
           
           Limit applies to the first list of tuples returned.
        """
        
        execute = self.execute
        
        if not start or start < prefix:
            start = strprevling(prefix)
        nextling = strnextling(prefix)
        
        q = ("select distinct n.path, v.serial "
             "from attributes a, versions v, nodes n "
             "where v.serial = (select max(serial) "
                              "from versions "
                              "where node = v.node and mtime < ?) "
             "and v.cluster != ? "
             "and v.node in (select node "
                           "from nodes "
                           "where parent = ?) "
             "and a.serial = v.serial "
             "and n.node = v.node "
             "and n.path > ? and n.path < ?")
        args = [before, except_cluster, parent, start, nextling]
        
        subq, subargs = self._construct_paths(pathq)
        if subq is not None:
            q += subq
            args += subargs
        subq, subargs = self._construct_filters(filterq)
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
            path, serial = props
            idx = path.find(delimiter, pfz)
            
            if idx < 0:
                mappend(props)
                count += 1
                if count >= limit:
                    break
                continue
            
            pf = path[:idx + dz]
            pappend(pf)
            if idx + dz == len(path):
                mappend(props)
                count += 1
            if count >= limit: 
                break
            
            args[3] = strnextling(pf) # New start.
            execute(q, args)
        
        return matches, prefixes
